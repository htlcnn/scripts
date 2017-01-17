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
import datetime
import os
import random
import sqlite3
import subprocess as spr
import sys
import telnetlib
import time


#====config====
DEVICE_IP = '10.0.0.204' # todo: find IP, input IP
DB = 'ZKDB.db'
DB_PATH = '/mnt/mtdblock/data/ZKDB.db'


def get_server_ip():
    try:
        import netifaces as ni
    except ImportError:
        import pip
        pip.main('install netifaces'.split())
        import netifaces as ni

    for i in ni.interfaces():
        info = ni.ifaddresses(i).get(ni.AF_INET)
        if info and DEVICE_IP[:DEVICE_IP.rfind('.')] in info[0]['addr']:
            return info[0]['addr']

        
def transfer_file(from_ip, to_ip, file_path, cmd='ftpput'):
    '''
    Transfer file from from_ip to to_ip via telnet.
    cmd is default to ftpput. Change to ftpget if needed.
    '''
    
    server_ip = get_server_ip()
    
    #====FTP Server====
    try:
        import pyftpdlib
    except ImportError:
        import pip
        pip.main('install pyftpdlib'.split())
        import pyftpdlib

    # start pyftpdlib FTP server: anonymous with write permission, port 2121    
    ftp_server = spr.Popen([sys.executable, '-m', 'pyftpdlib', '-w'])
    print('Server started')
    time.sleep(1)

    s = telnetlib.Telnet(DEVICE_IP)
    print(s.read_until(b'login: ').decode())
    s.write(b'root \n')
    print(s.read_until(b'Password: ').decode())
    s.write(b'solokey\n')
    if s.read_until(b'#'):
        s.write(bytes('ls %s\n' % DB_PATH, 'utf-8'))
        files = s.read_until(b'#').decode()

        if DB in files:
            if cmd == 'ftpput':
                command = bytes('%s -P 2121 %s %s %s\n' % (cmd, server_ip, DB, DB_PATH), 'utf-8')
            elif cmd == 'ftpget':
                command = bytes('%s -P 2121 %s %s %s\n' % (cmd, server_ip, DB_PATH, DB), 'utf-8')
            s.write(command)
            print(s.read_until(b'#').decode())

    # stop pyftpdlib FTP server
    ftp_server.kill()
    print('Server killed')
    
    
def add_log(uid, date, status):
    '''
    Edit ZKDB.db file, ATT_LOG table,
    insert a row which represents a check in/out log
    uid: User PIN
    date: follow format: dd/mm/yyyy - 14/01/2017
    status: 'in' is checking in, 'out' is checking out
    '''
    # verify_type: 0 is password, 1 is fingerprint
    verify_type = random.randint(0, 1)

    if status == 'in': # check in
        status = 0
        hour = 7
        minute = random.randint(50, 59)
        second = random.randint(0, 59)
    elif status == 'out': # check out
        status = 1
        hour = 17
        minute = random.randint(0, 19)
        second = random.randint(0, 59)
    else:
        raise ValueError('status must be `in` or `out`')

    time = datetime.time(hour, minute, second)
    date = datetime.datetime.strptime(date, '%d/%m/%Y')
    combined = datetime.datetime.combine(date, time)
    verify_time = datetime.datetime.strftime(combined, '%Y-%m-%dT%H:%M:%S')

    with sqlite3.connect(DB) as conn:
        query = ('INSERT INTO ATT_LOG (User_PIN, Verify_Type, Verify_Time, Status, Work_Code_ID, SEND_FLAG) '
                 'VALUES ({}, {}, "{}", {}, 0, 0)').format(uid, verify_type, verify_time, status, 0, 0)
        cur = conn.execute(query)
        
    print_log(uid, verify_type, verify_time, status)


def delete_log(log_id):
    '''
    Delete a log row with ID=log_id
    '''
    with sqlite3.connect(DB) as conn:
        query = ('DELETE FROM ATT_LOG WHERE ID={}'.format(log_id))
        cur = conn.execute(query)
    
    
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
        query = ('SELECT ID, User_PIN, Verify_Type, Verify_Time, Status FROM ATT_LOG '
                'WHERE User_PIN = {}'.format(uid))
        cur = conn.execute(query)
        rows = cur.fetchall()
    
    ret = []
    for row in rows:
        log_date = datetime.datetime.strptime(row[2], '%Y-%m-%dT%H:%M:%S')
        if log_date >= start_date and log_date <= end_date + datetime.timedelta(days=1):
            ret.append(row)
    return ret


def print_log(*log_row):
    '''
    Pretty print a log row
    log row format: (User_PIN, Verify_Type, Verify_Time, Status)
    '''
    uid = log_row[0]
    date = log_row[2]
    if log_row[-1] == 1:
        status = 'Check out'
    elif log_row[-1] == 0:
        status = 'Check in'
    print('{} {} at {}'.format(uid, status, date))


def check_log(log_row):
    '''
    Each day must have exactly 2 logs.
    One for checking in, before 8:00:00
    One for checking out, after 17:00:00
    Return True if satisfies all conditions, else False
    '''
    in_time = datetime.time(8, 0, 0)
    out_time = datetime.time(17, 0, 0)

    log_date = datetime.datetime.strptime(log_row[2], '%Y-%m-%dT%H:%M:%S')


    if log_row[-1] == 1 and log_date.time() < out_time:
        print('Early log on {}: {}'.format(date.date(), log_date))
        return False
    elif log_row[-1] == 0 and log_date.time() > in_time:
        print('Late log on {}: {}'.format(date.date(), log_date))
        return False
    else:
        return True
    

if __name__ == '__main__':
    pass
#     transfer_file(DEVICE_IP, server_ip, DB_PATH, cmd='ftpput')
#     add_log(514, '15/01/2017', 'in')
#     add_log(516, '15/01/2017', 'in')
#     transfer_file(server_ip, DEVICE_IP, DB_PATH, cmd='ftpget')
#     transfer_file(DEVICE_IP, server_ip, DB_PATH, cmd='ftpput')
