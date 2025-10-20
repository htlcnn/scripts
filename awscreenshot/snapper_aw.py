# aw_watcher_packaged.py
# Self-contained Windows screenshot watcher
# - Ensures NirCmd & FFmpeg (auto-download/unzip if missing)
# - Captures screenshots periodically (multi-monitor via savescreenshotfull; fallback to savescreenshot)
# - Compacts images by (user, day) for days strictly < today into H.264 MP4 (mpdecimate), then deletes images
# - Optional ActivityWatch heartbeat (best-effort)
# - Robust single-instance locks with stale cleanup
# - Creates Startup shortcut (.lnk) so it runs at logon without Task Scheduler

import os, sys, time, datetime, subprocess, traceback, shutil, zipfile, urllib.request, re, getpass, atexit

# ========= USER CONFIG =========
BASE_DIR = os.path.expanduser(r"e:\awscreenshot")  # thư mục gốc
INTERVAL_SEC = 60  # chu kỳ chụp (giây)
COMPACT_EVERY_SEC = 600  # chu kỳ gom/ghép (giây)
MIN_FRAMES_PER_VIDEO = 8  # < thì bỏ qua
TARGET_FPS = 1  # ảnh/giây khi phát video
CRF = 28  # x264 CRF (22 đẹp hơn, 30 nhẹ hơn)
PRESET = "veryfast"  # x264 preset

# Nguồn tải công cụ
NIR_URL = "https://www.nirsoft.net/utils/nircmd-x64.zip"
FF_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# ActivityWatch (tuỳ chọn)
AW_BUCKET_ID = "screenshots"
# =================================

# Layout
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
NIRDIR = os.path.join(TOOLS_DIR, "nircmd-x64")
FFDIR = os.path.join(TOOLS_DIR, "ffmpeg")
NIR_EXE = os.path.join(NIRDIR, "nircmd.exe")
FFMPEG_EXE = os.path.join(FFDIR, "ffmpeg.exe")

OUTDIR = BASE_DIR
VIDEO_DIR = os.path.join(BASE_DIR, "videos")

LOCK_DIR = os.path.join(BASE_DIR, "_locks")
MAIN_LOCK = os.path.join(LOCK_DIR, "runner.lock")
COMPACT_LOCK = os.path.join(LOCK_DIR, "compact.lock")

LOG_ERR = os.path.join(BASE_DIR, "error.log")
LOG_AWERR = os.path.join(BASE_DIR, "aw_errors.log")
LOG_FFERR = os.path.join(BASE_DIR, "ffmpeg_errors.log")

USERNAME_PREFIX = (os.environ.get("USERNAME") or getpass.getuser() or "user").replace(
    " ", "_"
)

# Ensure directories
for d in (OUTDIR, VIDEO_DIR, TOOLS_DIR, LOCK_DIR):
    os.makedirs(d, exist_ok=True)


def log_append(path, text):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
    except Exception:
        pass


# ---------- Download / Unzip ----------
def download(url, outpath):
    urllib.request.urlretrieve(url, outpath)


def unzip(zip_path, extract_dir):
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)


def ensure_nircmd():
    if os.path.exists(NIR_EXE):
        return NIR_EXE
    os.makedirs(NIRDIR, exist_ok=True)
    tmp = os.path.join(NIRDIR, "nircmd.zip")
    try:
        download(NIR_URL, tmp)
        unzip(tmp, NIRDIR)
    finally:
        try:
            os.remove(tmp)
        except:
            pass
    return NIR_EXE if os.path.exists(NIR_EXE) else None


def ensure_ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    if os.path.exists(FFMPEG_EXE):
        return FFMPEG_EXE
    os.makedirs(FFDIR, exist_ok=True)
    tmp = os.path.join(FFDIR, "ffmpeg.zip")
    try:
        download(FF_URL, tmp)
        unzip(tmp, FFDIR)
    finally:
        try:
            os.remove(tmp)
        except:
            pass
    for root, _, files in os.walk(FFDIR):
        if "ffmpeg.exe" in files:
            return os.path.join(root, "ffmpeg.exe")
    return None


NIR = ensure_nircmd()
FFMPEG = ensure_ffmpeg()


# ---------- Startup Shortcut (.lnk) ----------
def _find_pythonw():
    # ưu tiên pythonw
    exe = sys.executable
    if exe and exe.lower().endswith("pythonw.exe") and os.path.exists(exe):
        return exe
    # thử cùng thư mục với python.exe
    if exe and exe.lower().endswith("python.exe"):
        cand = exe[:-9] + "pythonw.exe"
        if os.path.exists(cand):
            return cand
    # thử trong PATH
    pw = shutil.which("pythonw")
    if pw:
        return pw
    # fallback python.exe (vẫn chạy được nhưng có cửa sổ nếu không dùng creationflags)
    return sys.executable


def _startup_dirs():
    # All Users Startup (yêu cầu quyền admin)
    pd = os.environ.get("PROGRAMDATA")
    if pd:
        yield os.path.join(pd, r"Microsoft\Windows\Start Menu\Programs\StartUp")
    # Current User Startup (không cần admin)
    app = os.environ.get("APPDATA")
    if app:
        yield os.path.join(app, r"Microsoft\Windows\Start Menu\Programs\Startup")


def ensure_startup_shortcut():
    """
    Tạo shortcut .lnk để tự chạy khi logon.
    Ưu tiên All Users; nếu không ghi được thì fallback user hiện tại.
    """
    pythonw = _find_pythonw()
    script = os.path.abspath(sys.argv[0])
    workdir = os.path.dirname(script)
    name = "AW Screenshot Watcher.lnk"

    for sdir in _startup_dirs():
        try:
            if not os.path.isdir(sdir):
                continue
            lnk_path = os.path.join(sdir, name)
            # nếu đã tồn tại và đúng target thì bỏ qua
            if os.path.exists(lnk_path):
                # thử đọc qua powershell (nếu cần update)
                try:
                    # dùng PowerShell để kiểm tra target path
                    ps = [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-Command",
                        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk_path}');"
                        f"Write-Output $s.TargetPath;Write-Output $s.Arguments;",
                    ]
                    out = subprocess.run(ps, capture_output=True, text=True, timeout=5)
                    tp = (out.stdout or "").splitlines()
                    cur_target = tp[0].strip() if tp else ""
                    cur_args = tp[1].strip() if len(tp) > 1 else ""
                    want_args = f'"{script}"'
                    if (
                        os.path.normcase(cur_target) == os.path.normcase(pythonw)
                        and cur_args == want_args
                    ):
                        return lnk_path
                except Exception:
                    pass  # nếu không đọc được thì sẽ ghi đè

            # tạo/ghi đè shortcut bằng PowerShell (không cần pywin32)
            ps_cmd = (
                "$s=New-Object -ComObject WScript.Shell;"
                f"$lnk=$s.CreateShortcut('{lnk_path}');"
                f"$lnk.TargetPath='{pythonw}';"
                f"$lnk.Arguments='\"{script}\"';"
                f"$lnk.WorkingDirectory='{workdir}';"
                f"$lnk.IconLocation='{pythonw},0';"
                "$lnk.Save();"
            )
            res = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps_cmd,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0 and os.path.exists(lnk_path):
                return lnk_path
        except Exception as e:
            # thử thư mục Startup tiếp theo
            log_append(LOG_ERR, f"ensure_startup_shortcut error at {sdir}: {repr(e)}")
    # nếu không tạo được ở cả hai nơi, ghi log nhưng không chặn chạy
    log_append(LOG_ERR, "Failed to create Startup shortcut in all known locations.")
    return None


# tạo shortcut ngay khi chạy (không chặn luồng)
try:
    ensure_startup_shortcut()
except Exception as e:
    log_append(LOG_ERR, f"startup_shortcut_exception: {repr(e)}")

# ---------- Robust Locks with Stale Cleanup ----------
_LOCK_PID_RE = re.compile(r"\bpid\s*=\s*(\d+)", re.I)


def _pid_running_psutil(pid: int) -> bool:
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        return False


def _pid_running_tasklist(pid: int) -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        text = (out.stdout or "") + (out.stderr or "")
        return (str(pid) in text) and ("No tasks are running" not in text)
    except Exception:
        return False


def _pid_running_oskill(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def is_pid_running(pid: int) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    return (
        _pid_running_psutil(pid)
        or _pid_running_tasklist(pid)
        or _pid_running_oskill(pid)
    )


def _read_lock_pid(lock_path: str):
    try:
        with open(lock_path, "r", encoding="utf-8", errors="ignore") as f:
            m = _LOCK_PID_RE.search(f.read())
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return None


def try_acquire_lock(lock_path: str, stale_after_seconds: int = 3600) -> bool:
    # Attempt atomic create
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(f"pid={os.getpid()} time={time.time()}\n")
        return True
    except FileExistsError:
        pass

    # Existing lock: check staleness
    pid = _read_lock_pid(lock_path)
    try:
        mtime = os.path.getmtime(lock_path)
    except Exception:
        mtime = 0.0

    alive = is_pid_running(pid) if pid is not None else False
    too_old = (time.time() - mtime) > max(60, stale_after_seconds)

    if (not alive) or too_old:
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass
        except Exception:
            return False
        # Try again
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as f:
                f.write(f"pid={os.getpid()} time={time.time()}\n")
            return True
        except FileExistsError:
            return False
    else:
        return False


def release_lock(lock_path: str):
    try:
        pid = _read_lock_pid(lock_path)
        if pid is None or pid == os.getpid():
            os.remove(lock_path)
    except FileNotFoundError:
        pass
    except Exception:
        pass


def ensure_no_stale_locks():
    for lock_path in (MAIN_LOCK, COMPACT_LOCK):
        pid = _read_lock_pid(lock_path)
        if pid and not is_pid_running(pid):
            try:
                os.remove(lock_path)
                log_append(LOG_ERR, f"Cleaned stale lock {lock_path} (pid={pid})")
            except Exception:
                pass


# ---------- ActivityWatch (optional) ----------
aw = None
EventCls = None
try:
    from aw_client import ActivityWatchClient

    try:
        from aw_core.models import Event as EventCls
    except Exception:
        EventCls = None
    try:
        aw = ActivityWatchClient("aw-watcher-screenshot", testing=False)
        aw.connect()
        try:
            aw.create_bucket(AW_BUCKET_ID, "event")
        except Exception:
            pass
    except Exception:
        aw = None
except Exception:
    aw = None


def make_event(ts, path):
    if EventCls is not None:
        return EventCls(timestamp=ts, duration=0, data={"file": path})

    class _Evt:
        def __init__(self, ts, path):
            self._ts, self._path = ts, path

        def to_json_dict(self):
            return {
                "timestamp": self._ts.isoformat(),
                "duration": 0,
                "data": {"file": self._path},
            }

    return _Evt(ts, path)


# ---------- Capture ----------
def _nircmd_capture(out_path: str) -> bool:
    if not NIR or not os.path.exists(NIR):
        raise RuntimeError("NirCmd not available")
    # Try full desktop first
    try:
        subprocess.run([NIR, "savescreenshotfull", out_path], check=False)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return True
    except Exception:
        pass
    # Fallback
    try:
        subprocess.run([NIR, "savescreenshot", out_path], check=False)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return True
    except Exception:
        pass
    return False


def snap_once():
    ts = datetime.datetime.now().astimezone()
    ts_str = ts.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUTDIR, f"{USERNAME_PREFIX}_snap_{ts_str}.png")
    try:
        ok = _nircmd_capture(out_path)
        if not ok:
            raise RuntimeError("NirCmd capture failed (no output)")
    except Exception:
        log_append(
            LOG_ERR, f"{ts.isoformat()} | capture-error\n{traceback.format_exc()}"
        )
        return

    if aw:
        try:
            ev = make_event(ts, out_path)
            aw.heartbeat(AW_BUCKET_ID, ev, pulsetime=10)
        except Exception:
            log_append(LOG_AWERR, f"{ts.isoformat()} | {traceback.format_exc()}")


# ---------- Video Compact ----------
def _safe_concat_path(p: str) -> str:
    return p.replace("\\", "/").replace("'", "'\\''")


def _parse_user_and_day(path: str):
    """
    Expect: <user>_snap_YYYYMMDD_HHMMSS.png
    Fallback: ('unknown', mtime day)
    """
    base = os.path.basename(path)
    m = re.search(r"^([^_]+)_.*?(\d{8})_(\d{6})", base)
    if m:
        return m.group(1), m.group(2)
    dt = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    return "unknown", dt.strftime("%Y%m%d")


def _build_concat_list(images, list_path):
    with open(list_path, "w", encoding="utf-8") as f:
        for img in images:
            f.write(f"file '{_safe_concat_path(img)}'\n")
            f.write(f"duration {1.0 / max(1, TARGET_FPS):.6f}\n")
        if images:
            f.write(f"file '{_safe_concat_path(images[-1])}'\n")


def _make_video_for_user_day(user: str, day_str: str, images: list):
    """Ghép video cho 1 user trong 1 ngày, ffmpeg chạy ẩn, mpdecimate loại frame trùng."""
    if not FFMPEG or not os.path.exists(FFMPEG):
        return False, "ffmpeg-not-found"
    if not images or len(images) < MIN_FRAMES_PER_VIDEO:
        return False, "not-enough-frames"

    images = sorted(images)
    list_path = os.path.join(OUTDIR, f"filelist_{user}_{day_str}.txt")
    _build_concat_list(images, list_path)

    out_mp4 = os.path.join(VIDEO_DIR, f"aw_{user}_{day_str}.mp4")
    cmd = [
        FFMPEG,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
        "-vf",
        f"mpdecimate,setpts=N/({TARGET_FPS})/TB",
        "-c:v",
        "libx264",
        "-preset",
        PRESET,
        "-crf",
        str(CRF),
        "-pix_fmt",
        "yuv420p",
        out_mp4,
    ]

    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE

    try:
        try:
            with open(
                os.path.join(OUTDIR, "ffmpeg_cmd.log"), "a", encoding="utf-8"
            ) as f:
                f.write(" ".join(cmd) + "\n")
        except Exception:
            pass

        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=si,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        ok = (
            (res.returncode == 0)
            and os.path.exists(out_mp4)
            and os.path.getsize(out_mp4) > 0
        )
        if ok:
            try:
                os.remove(list_path)
            except:
                pass
            for p in images:
                try:
                    os.remove(p)
                except:
                    pass
            return True, out_mp4
        else:
            try:
                with open(LOG_FFERR, "a", encoding="utf-8") as f:
                    f.write(
                        res.stderr.decode("utf-8", errors="ignore") or "ffmpeg failed"
                    )
                    f.write("\n")
            except Exception:
                pass
            return False, "ffmpeg-failed"

    except Exception as e:
        try:
            with open(LOG_FFERR, "a", encoding="utf-8") as f:
                f.write(f"{user}_{day_str} | {repr(e)}\n")
        except Exception:
            pass
        return False, "exception"


def compact_old_days_to_videos():
    if not FFMPEG or not os.path.exists(FFMPEG):
        return
    if not try_acquire_lock(
        COMPACT_LOCK, stale_after_seconds=max(1800, COMPACT_EVERY_SEC * 3)
    ):
        return
    try:
        today = datetime.datetime.now().strftime("%Y%m%d")
        images_by_key = {}  # (user, day) -> [paths]
        for name in os.listdir(OUTDIR):
            if not name.lower().endswith(".png"):
                continue
            p = os.path.join(OUTDIR, name)
            if not os.path.isfile(p):
                continue
            user, day = _parse_user_and_day(p)
            if day >= today:
                continue  # chỉ ghép ngày cũ hơn hôm nay
            images_by_key.setdefault((user, day), []).append(p)

        for (user, day), imgs in sorted(
            images_by_key.items(), key=lambda x: (x[0][0], x[0][1])
        ):
            _make_video_for_user_day(user, day, imgs)
    finally:
        release_lock(COMPACT_LOCK)


# ---------- Main ----------
def _cleanup_lock_on_exit():
    try:
        release_lock(MAIN_LOCK)
    except Exception:
        pass


def main():
    ensure_no_stale_locks()

    if not try_acquire_lock(
        MAIN_LOCK, stale_after_seconds=max(1800, COMPACT_EVERY_SEC * 3)
    ):
        return

    atexit.register(_cleanup_lock_on_exit)
    log_append(
        LOG_ERR, f"[{datetime.datetime.now().isoformat()}] START pid={os.getpid()}"
    )

    try:
        last_compact = 0
        while True:
            snap_once()
            now = time.time()
            if now - last_compact > COMPACT_EVERY_SEC:
                compact_old_days_to_videos()
                last_compact = now
            time.sleep(INTERVAL_SEC)
    except KeyboardInterrupt:
        pass
    except Exception:
        log_append(
            LOG_ERR,
            f"{datetime.datetime.now().astimezone().isoformat()} | fatal\n{traceback.format_exc()}",
        )
    finally:
        release_lock(MAIN_LOCK)
        log_append(
            LOG_ERR, f"[{datetime.datetime.now().isoformat()}] EXIT pid={os.getpid()}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_append(
            LOG_ERR,
            f"{datetime.datetime.now().astimezone().isoformat()} | fatal-top\n{traceback.format_exc()}",
        )
