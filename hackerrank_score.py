#!/usr/bin/env python3
'''
Get Python Archive score on hackerrank
Usage: hackerrank_score.py user1 user2 ...
'''

import argparse
import requests


def get_hackerrank_score():
    parser = argparse.ArgumentParser()
    parser.add_argument('users', help='Usernames to get score',
                        default=['hoangthanhlong'], nargs='*')

    args = parser.parse_args()

    ret = []

    for user in args.users:
        url = 'https://www.hackerrank.com/rest/hackers/{}/scores'.format(user)
        res = requests.get(url)
        if res.status_code == 200:
            for field in res.json():
                if field['name'] == 'Python':
                    ret.append('{}: {:.0f}'.format(user,
                                               field['practice']['score']))
        else:
            ret.append('{}: Not found'.format(user))
    return ret

if __name__ == '__main__':
    for info in get_hackerrank_score():
        print(info)
