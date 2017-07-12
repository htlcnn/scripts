"""
You may start IDM from the command line using the following parameters
idman /s
or idman /d URL [/p local_path] [/f local_file_name] [/q] [/h][/n] [/a]
Parameters:
/d URL - downloads a file
e.g. IDMan.exe /d "http://www.internetdownloadmanager.com/path/FileName.zip"
/s - starts queue in scheduler
/p local_path - defines the local path where to save the file
/f local_file_name - defines the local file name to save the file
/q - IDM will exit after the successful downloading. This parameter works only for the first copy
/h - IDM will hang up your connection after the successful downloading
/n - turns on the silent mode when IDM doesn't ask any questions
/a - add a file specified with /d to download queue, but don't start downloading
Parameters /a, /h, /n, /q, /f local_file_name, /p local_path work only if you specified the file to download with /d URL
Examples
C:\>idman.exe /n /d http://www.tonec.com/download/idman317.exe

or faster method: using COM to send 112 links to IDM (5s vs 15s)
"""
import subprocess
import os
import sys
import requests
import lxml.html
import string
sys.path.append("E:\\Setup\\coding\\python")
import htl.idm

def get_download_links(page_url):
    resp = requests.get(page_url)
    doc = lxml.html.fromstring(resp.text)
    lectures = doc.cssselect('.course-item-list-section-list>li')
    download_links = []
    counter = 0
    for lecture in lectures:
        lecture_name = lecture.cssselect('a.lecture-link')[0].text
        lecture_name = str(counter) + "." + normalize_string(lecture_name) + ".mp4"
        lecture_download_link = lecture.cssselect('.course-lecture-item-resource>a:last-child')[0].attrib['href']
        # print(lecture_download_link, lecture_name)
        download_links.append((lecture_download_link, lecture_name))
        counter += 1
    return download_links

def normalize_string(input_str):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    output_str = ''.join(c for c in input_str if c in valid_chars)
    return output_str

if __name__ == '__main__':
    page_url = 'https://class.coursera.org/startup-001/lecture'
    links = get_download_links(page_url)
    for link in links:
        htl.idm.send_link_to_idm(link=link[0], file_name=link[1])
        print(link[0], link[1])
