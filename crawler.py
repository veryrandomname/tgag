import os
from io import BytesIO
from urllib.parse import urlparse

import requests
import json
import shutil
import sys
import schedule
from werkzeug.datastructures import FileStorage
import praw

import dbclient
from util import get_file_extension, generate_unique_filename, gif_stream_to_mp4_stream, image_stream_to_webp_stream

root_path = '/home/fettundledig/Programmieren/tgag'

db = dbclient.MyClient(root_path)

reddit = praw.Reddit(
    client_id="9GpL6uM70--UJA",
    client_secret="O2hIcFUUjpFZbxpytwqEO3WG9JY",
    user_agent="swepe_meme_downloader:1.0"
)


def crawl_subreddit(subreddit_name, user, limit=20):
    for submission in reddit.subreddit(subreddit_name).hot(limit=limit):
        if submission.url and submission.title:
            print(submission.title)
            parsed_url = urlparse(submission.url)
            filename = os.path.basename(parsed_url.path)
            filename_without_extension, file_extension = os.path.splitext(filename)
            file_extension = file_extension[1:]

            img_response = requests.get(submission.url, stream=True)
            stream = BytesIO(img_response.content)
            if file_extension == "gif":
                stream = gif_stream_to_mp4_stream(stream)
                file_extension = "mp4"
            if file_extension in tuple('jpg jpe jpeg png'.split()):
                stream = image_stream_to_webp_stream(stream, file_extension)
                file_extension = "webp"

            db.send_pic(stream, user, file_extension, submission.title, False)


db.add_user("trippinthroughtime", "3fYfvg92NkV0U", True)
crawl_subreddit("trippinthroughtime", "trippinthroughtime")


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
    for child in children:
        meme = child["data"]
        url = meme["url"]
        title = meme['title']
        if url and title:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)

            file_extension = get_file_extension(filename)

            img_response = requests.get(url, stream=True)
            out_file = BytesIO(img_response.content)
            db.send_pic(out_file, "cockblockula", file_extension, title, False)

# job(0)
# schedule.every().day.at("6:00").do(job, 'downloading memes')
