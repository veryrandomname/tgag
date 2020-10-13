import os
from io import BytesIO
from urllib.parse import urlparse

import requests
import json
import shutil
import sys
import schedule
from werkzeug.datastructures import FileStorage

import dbclient
from util import get_file_extension

db = dbclient.MyClient('/home/fettundledig/Programmieren/tgag')


def job(t):
    baseurl = "http://www.reddit.com/r/dankmemes/.json"

    if len(sys.argv) > 1:
        after = sys.argv[1]
    else:
        after = ""

    if after:
        requesturl = baseurl + f'/after={after}'
    else:
        requesturl = baseurl

    print(requesturl)
    r = requests.get(requesturl, headers={'User-agent': 'overweight kid'})

    json_response = r.json()

    children = json_response["data"]["children"]
    for child in children[:3]:
        meme = child["data"]
        url = meme["url"]
        title = meme['title']
        if url and title:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)

            file_extension = get_file_extension(filename)

            img_response = requests.get(url, stream=True)
            out_file = BytesIO(img_response.content)
            db.send_pic(out_file, "cockblockula", file_extension, title)


job(0)
# schedule.every().day.at("6:00").do(job, 'downloading memes')
