'''
This script will do auto-check in/out for ZMM100 fingerprint access control
device by ZKSoftware.

At my office, the manager uses an application to load data from the
fingerprint device. After he loads data, log in device's database is cleared.
So in my case, I write this script to automate checking in/out everyday.

Device is running linux with busybox, so I have access to ftpput, ftpget and
wget commands (ftpd is missing). Data is stored in /mnt/mtdblock/data/ZKDB.db.
This is a sqlite3 database file. User info is in USER_INFO, user transactions
are in ATT_LOG table.

Procedure:
- telnet into the device
- ftpput database file at /mnt/mtdblock/data/ZKDB.db to a temporary FTP server
- edit ZKDB.db file on server
- ftpget ZKDB.db from FTP server
'''
import argparse
import datetime
import os
import random
import sqlite3
import subprocess as spr
import sys
import telnetlib


def get_server_ip(device_ip):
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((device_ip, 80))
    return s.getsockname()[0]


def transfer_file(from_ip, to_ip, remote_file_path, cmd='ftpput'):
    '''
    Transfer file from from_ip to to_ip via telnet.
    Use ftpput and ftpget.

    '''

    # ====FTP Server====
    try:
        import pyftpdlib
    except ImportError:
        import pip
        pip.main('install pyftpdlib'.split())

    # start pyftpdlib FTP server: anonymous with write permission, port 2121
    ftp_server = spr.Popen([sys.executable, '-m', 'pyftpdlib', '-w'])
    print('Server started')
    filename = os.path.basename(remote_file_path)

    s = telnetlib.Telnet(DEVICE_IP)
    print(s.read_until(b'login: ').decode())
    s.write(b'root \n')
    print(s.read_until(b'Password: ').decode())
    s.write(b'solokey\n')
    if s.read_until(b'#'):
        s.write(bytes('ls %s\n' % DB_PATH, 'utf-8'))
        files = s.read_until(b'#').decode()

        if filename in files:
            while True:
                if cmd == 'ftpput':
                    command = bytes('%s -P 2121 %s %s %s\n' % (cmd, server_ip,
                                                               filename,
                                                               remote_file_path),
                                    'utf-8')
                elif cmd == 'ftpget':
                    command = bytes('%s -P 2121 %s %s %s\n' % (cmd, server_ip, remote_file_path, filename), 'utf-8')
                else:
                    raise ValueError('cmd must be `ftpput` or `ftpget`')
                s.write(command)
                ret = s.read_until(b'#').decode()
                if 'refused' not in ret:
                    print(ret)
                    break

    # stop pyftpdlib FTP server
    ftp_server.kill()
    print('Server killed')


def generate_verify_time(status='in', late=False):
    '''
    Generate normal verify time based on status `in` or `out`
    `in` time will be random 10 mins before 8:00
    `out` time will be random 10 mins after 17:00
    '''
    if status == 'in':
        status = 0
        if not late:
            hour = 7
            minute = random.randint(50, 59)
        else:
            hour = 8
            minute = random.randint(15, 20)
    elif status == 'out':
        status = 1
        hour = 17
        minute = random.randint(0, 10)
    else:
        raise ValueError('status must be `in` or `out`')

    second = random.randint(0, 59)
    time = datetime.time(hour, minute, second)

    return time


def add_log(uid, date, status, late=False):
    '''
    Edit ZKDB.db file, ATT_LOG table,
    insert a row which represents a check in/out log
    uid: User PIN
    date: follow format: dd/mm/yyyy - 14/01/2017
    status: 'in' is checking in, 'out' is checking out
    '''
    # verify_type: 0 is password, 1 is fingerprint
    verify_type = 1

    if status == 'in':
        status = 0
        time = generate_verify_time('in', late=late)

    elif status == 'out':
        status = 1
        time = generate_verify_time('out')
    else:
        raise ValueError('status must be `in` or `out`')

    date = datetime.datetime.strptime(date, '%d/%m/%Y')
    combined = datetime.datetime.combine(date, time)
    verify_time = '{:%Y-%m-%dT%H:%M:%S}'.format(combined)

    with sqlite3.connect(DB) as conn:
        query = ('INSERT INTO ATT_LOG (User_PIN, Verify_Type, Verify_Time, '
                 'Status, Work_Code_ID, SEND_FLAG) '
                 'VALUES ({}, {}, "{}", {}, 0, 0)').format(uid, verify_type,
                                                           verify_time, status,
                                                           0, 0)
        cur = conn.execute(query)
        cur = conn.execute('SELECT last_insert_rowid() FROM ATT_LOG')
        r = cur.fetchone()

    print_log(r, uid, verify_type, verify_time, status)

def add_logs(uid, start, end, status, late=False):
    start_date = datetime.datetime.strptime(start, '%d/%m/%Y')
    end_date = datetime.datetime.strptime(end, '%d/%m/%Y')
    day_count = end_date - start_date
    day_count = day_count.days + 1
    for date in (start_date + datetime.timedelta(i) for i in range(day_count)):
        date = '{:%d/%m/%Y}'.format(date)
        add_log(uid, date, status, late)


def delete_log(log_id):
    '''
    Delete a log row with ID=log_id
    '''
    with sqlite3.connect(DB) as conn:
        query = ('DELETE FROM ATT_LOG WHERE ID={}'.format(log_id))
        conn.execute(query)
    print('Deleted log {}'.format(log_id))


def get_logs(uid, start_date, end_date):
    '''
    Returns logs of 'uid' from 'start_date' to 'end_date'
    uid: User PIN
    start_date: follow format 14/01/2017
    end_date: follow format 15/01/2017
    Return format: list of (ID, User_PIN, Verify_Type, Verify_Time, Status)
    '''
    start_date = datetime.datetime.strptime(start_date, '%d/%m/%Y')
    end_date = datetime.datetime.strptime(end_date, '%d/%m/%Y')

    with sqlite3.connect(DB) as conn:
        query = ('SELECT ID, User_PIN, Verify_Type, Verify_Time, Status '
                 'FROM ATT_LOG WHERE User_PIN = {}'.format(uid))
        cur = conn.execute(query)
        rows = cur.fetchall()

    ret = []
    for row in rows:
        log_date = datetime.datetime.strptime(row[-2], '%Y-%m-%dT%H:%M:%S')
        if log_date >= start_date and log_date <= end_date + datetime.timedelta(days=1):
            ret.append(row)
    return ret


def get_logs_by_date(uid, date):
    return get_logs(uid, date, date)


def print_log(*log_row):
    '''
    Pretty print a log row
    log row format: (ID, User_PIN, Verify_Type, Verify_Time, Status)
    '''
    id, uid, verify_type, verify_time, status = log_row

    if status == 1:
        status = 'Check out'
    elif status == 0:
        status = 'Check in'
    print('{}. {} {} at {}'.format(id, uid, status, verify_time))


def check_log_row(log_row):
    '''
    Each day must have exactly 2 logs.
    One for checking in, before 8:00:00
    One for checking out, after 17:00:00
    Return True if satisfies all conditions, else False
    '''
    in_time = datetime.time(8, 0, 0)
    out_time = datetime.time(17, 0, 0)

    log_date = datetime.datetime.strptime(log_row[2], '%Y-%m-%dT%H:%M:%S')
    status = log_row[-1]

    if status == 1 and log_date.time() < out_time:
        print('Early log on {}: {}'.format(log_date.date(), log_date))
        return False
    elif status == 0 and log_date.time() > in_time:
        print('Late log on {}: {}'.format(log_date.date(), log_date))
        return False
    else:
        return True


def check_log_by_date(uid, date):
    pass


def fix_logs(uid, start_date, end_date):
    '''
    Fix logs of uid from start_date to end_date
    A normalized log contains 2 logs per day
    One check in log before 8:00
    One check out log after 17:00
    '''

    start_date = '{:%d/%m/%Y}'.format(start_date)
    end_date = '{:%d/%m/%Y}'.format(end_date)
    day_count = (end_date - start_date) + 1

    for date in (start_date + datetime.timedelta(i) for i in range(day_count)):
        date = '{:%d/%m/%Y}'.format(date.date)
        logs = get_logs_by_date(uid, date)
        if len(logs) == 2:
            if not check_log_row(logs[0]) or not check_log_row(logs[1]):
                delete_log(logs[0][0])
                delete_log(logs[1][0])
                add_log(uid, date, 'in')
                add_log(uid, date, 'out')
        elif len(logs) == 0:
            add_log(uid, date, 'in')
            add_log(uid, date, 'out')
        else:
            for log in logs:
                delete_log(log[0])
            add_log(uid, date, 'in')
            add_log(uid, date, 'out')


def main():

    today = '{:%d/%m/%Y}'.format(datetime.date.today())

    parser = argparse.ArgumentParser()
    parser.add_argument('action', help='`get`, `checkin`, `checkout`, '
                        '`add` or `fix` logs', default='get')
    parser.add_argument('uids', help='User PINs', type=int, nargs='*')
    parser.add_argument('-d', '--date', help='Date', default=today)
    parser.add_argument('-r', '--range',
                        help='Range of date, ex. 01/01/2017-02/01/2017')
    parser.add_argument('--log', help='log id to delete')
    parser.add_argument('--late', help='Checkin late or not',
                        action='store_true')

    args = parser.parse_args()
    uids = args.uids
    date = args.date or today
    if not args.range:
        start, end = date, date
    else:
        start, end = args.range.split('-')

    transfer_file(DEVICE_IP, server_ip, DB_PATH, cmd='ftpput')

    for uid in uids:
        if args.action == 'get':
            logs = get_logs(uid, start, end)
            for log in logs:
                print_log(*log)
        elif args.action == 'checkin':
            add_logs(uid, start, end, 'in', late=args.late)
        elif args.action == 'checkout':
            add_logs(uid, start, end, 'out')
        elif args.action == 'add':
            add_log(uid, start, end)
        elif args.action == 'fix':
            fix_logs(uid, start, end)
        elif args.action == 'delete':
            delete_log(args.log)
        else:
            raise ValueError('Action must be `get`, `checkin`, `checkout`, '
                             '`fix` or `delete`')

    transfer_file(server_ip, DEVICE_IP, DB_PATH, cmd='ftpget')


if __name__ == '__main__':
    # ====config====
    DEVICE_IP = '10.0.0.204'  # todo: find IP, input IP
    DB_PATH = '/mnt/mtdblock/data/ZKDB.db'
    DB = os.path.basename(DB_PATH)
    server_ip = get_server_ip(DEVICE_IP)

    main()
