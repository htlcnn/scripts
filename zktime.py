import argparse
import datetime
import random
from zk import ZK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', default='10.0.0.204')
    parser.add_argument('action', default='reset', choices=['reset', 'in', 'out'])
    parser.add_argument('-d', default='today', help='Date to set, format: dd/mm/yyyy')

    args = parser.parse_args()

    zk = ZK(args.ip)
    conn = zk.connect()

    if args.d == 'today':
        date_to_set = datetime.date.today()
    else:
        date_to_set = datetime.datetime.strptime(args.d, '%d/%m/%Y')


    if args.action == 'reset':
        time_to_set = datetime.datetime.today()

    if args.action == 'in':
        time = datetime.time(
                hour=7,
                minute=random.randint(50, 59),
                second=random.randint(0, 59)
                )
        time_to_set = datetime.datetime.combine(date_to_set, time)
        
    
    if args.action == 'out':
        time = datetime.time(
                hour=17,
                minute=random.randint(0, 15),
                second=random.randint(0, 59)
                )
        time_to_set = datetime.datetime.combine(date_to_set, time)

    conn.set_time(time_to_set)
    print('{}: Set time to {}'.format(args.action.upper(), time_to_set))


if __name__ == "__main__":
    main()
