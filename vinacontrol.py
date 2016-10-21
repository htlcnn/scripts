#!/usr/bin/env python3
'''
A script to get all questions from thuvien.vinacontrol.com.vn
input: username and password
'''
import argparse

import lxml.html
import pandas as pd
import requests


def parse_row(row):
    ret = []
    for col in row:
        if col.cssselect('ul>li'):
            ret.append('\n'.join([i.text_content() for i in col.cssselect('ul>li')]))
        else:
            ret.append(col.text_content().strip())
    return ret

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', help='Username')
    parser.add_argument('-p', '--password', help='Password')
    args = parser.parse_args()



    with requests.Session() as s:
        homepage = s.get('http://trithuc.vinacontrol.com.vn/')
        html = lxml.html.fromstring(homepage.text)

        payloads = {'name': args.username,
                    'pass': args.username,
                    'form_build_id': html.cssselect('input[name=form_build_id]')[0].attrib['value'],
                    'form_id': html.cssselect('input[name=form_id]')[0].attrib['value'],
                    'op': 'Đăng nhập'
                   }
        s.post('http://trithuc.vinacontrol.com.vn/node', data=payloads)
        res = s.get('http://trithuc.vinacontrol.com.vn/ds-cauhoi?field_quiz_phanloai_tid[0]=438&items_per_page=All')
        html = lxml.html.fromstring(res.text)
    table = html.cssselect('table[data-view-name=ds_cauhoi]')[0]
    columns = ['STT', 'Phân loại', 'Câu hỏi', 'Trả lời']
    df = pd.DataFrame(columns=columns)

    for row in table.cssselect('tbody>tr'):
        df = df.append(pd.DataFrame([parse_row(row)], columns=columns))

    df.to_excel('test.xls')


if __name__ == '__main__':
    main()
