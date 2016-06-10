import logging
import re

import requests


def get_star_and_fork(user, repo):
    global logger
    url = 'https://api.github.com/repos/{}/{}?client_id={}&client_secret={}'
    CLIENT_ID = '9237bea233afb6acfc3d'
    CLIENT_SECRET = '329c624b03b70df5d1cc335dfa926c3d63d5c44f'
    res = requests.get(url.format(user, repo, CLIENT_ID, CLIENT_SECRET))
    try:
        stars = res.json()['stargazers_count']
        forks = res.json()['forks_count']
        return (stars, forks)
    except Exception as e:
        logger.error(user, repo, res.json())
        raise e
        
def parse_link(md_links):
    global logger
    parsed_md_links = []
    count = 0
    for md_link in md_links:
        if 'https://github.com' in md_link:
            try:
                title, user, repo = re.match(r'\[(.+)\]\(https://github.com/([^/]+)/([^/^#]+)/*[^/]*\)', md_link).groups()
                stars, forks = get_star_and_fork(user, repo)
                txt = '[:octocat:{}](https://github.com/{}/{}) - :star: {} :fork_and_knife: {}'
                parsed_md_links.append(txt.format(title, user, repo, stars, forks))
                count += 1
                logger.debug('{}. Done {}/{}', count, user, repo)
            except Exception as e:
                parsed_md_links.append(md_link)
                logger.error('{} {}', md_link, e)
        else:
            title, link = re.match(r'\[(.+)\]\((.+)\)', md_link).groups()
            title = '[:earth_america:{}]'.format(title)
            parsed_md_links.append('[{}]({})'.format(title, link))
            count += 1
            logger.debug('{}. Done {}', count, link)
    return zip(md_links, parsed_md_links)

def main():
    # logging config
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.FileHandler("{}.log".format(__name__))
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
        
    # raise api limit from 60 req/h to 5000 req/h, enough for this script
    token = '11f9f5979c54d52801c9ed70756b2b4cd7a0136b'
    requests.get('https://api.github.com/user?access_token={}'.format(token)).headers
    
    # get source readme.md to parse
    res = requests.get('https://raw.githubusercontent.com/vinta/awesome-python/master/README.md')
    
    # get all links
    md_links = re.findall('.+(\[.+\]\(http[^\)]+\))+.+', res.text)
    replace_list = parse_link(md_links)
    for i in replace_list:
        print(i)
        
if __name__ == '__main__':
    main()