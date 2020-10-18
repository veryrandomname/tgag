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
from util import get_file_extension, generate_unique_filename, gif_stream_to_mp4_stream, image_stream_to_webp_stream, \
    load_config

config = load_config()

db = dbclient.MyClient(config["root_path"], address=("18.195.83.66", 6000))

reddit = praw.Reddit(
    client_id=config["reddit"]["username"],
    client_secret=config["reddit"]["password"],
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


for subreddit in config["subreddits"]:
    subreddit_name = subreddit["name"]
    db.add_user(subreddit_name, subreddit["password"], True)
    crawl_subreddit(subreddit_name,subreddit_name, 1000)

