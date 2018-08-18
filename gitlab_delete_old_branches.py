from datetime import datetime, timedelta
import os

import requests


token = os.getenv('gitlab-token')
project_id = os.getenv('gitlab-project-id')

res = requests.get('https://gitlab.com/api/v3/projects/{}/'
                    'repository/branches?private_token={}'.format(project_id, token))

for branch in res.json():
    committed_date = datetime.strptime(branch['commit']['committed_date'].split('T')[0],
                                                '%Y-%m-%d')
    days_from_last_commit = datetime.today() - committed_date
    print(branch['name'], branch['commit']['author_name'], committed_date)
    if days_from_last_commit > timedelta(days=30) and not branch['protected']:
        headers = {'PRIVATE-TOKEN': token}
        resx = requests.delete('https://gitlab.com/api/v3/projects/1591562'
                               '/repository/branches/{}'.format(branch['name']), headers=headers)
        print(resx.json())
