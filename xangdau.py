import argparse
import re

from bs4 import BeautifulSoup
import pandas as pd
import requests


def main():
    default_url = ('http://xangdau.net/thong-tin-chung/gia-ban-le/'
                   'gia-hien-tai-trong-nuoc/gia-ban-le-xang-dau-dang'
                   '-ap-dung-tu-15-h-ngay-20-12-2016-50037.html')
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='url of xangdau.net to scape data',
                        default=default_url)
    args = parser.parse_args()
    res = requests.get(args.url)
    soup = BeautifulSoup(res.text, 'lxml')
    title = soup.select('.details-news .entry-title')[0]
    time, date = re.match(r'.*từ (.+) ngày (.+)', title.text).groups()

    table = soup.find('table', {'class': 'MsoNormalTable'})
    df = pd.read_html(table.__str__(), header=0)[0]
    df.iloc[:, 1:3] = df.iloc[:, 1:3].apply(lambda x: x * 1000)
    info = df.iloc[:, :2].T
    info[8] = date
    info[9] = time
    info[10] = args.url

    info.to_excel('output.xls')
    print('Saved to output.xls')


if __name__ == "__main__":
    main()
