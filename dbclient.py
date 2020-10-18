import json
import os
import random
import shutil
import string
from multiprocessing.connection import Client

from util import generate_unique_filename, load_config

ALLOWED_EXTENSIONS = tuple('jpg jpe jpeg png webp webm mp4'.split())

config = load_config()

class MyClient:
    conn = None

    def __init__(self, root_path, address=('localhost', 6000), authkey=config["database"]["password"].encode()):
        self.conn = Client(address, authkey=authkey)
        self.root_path = root_path

    def create_thumbnail(self, filename):
        if not os.path.isfile(f"{self.root_path}/thumbnails/{filename}.webp"):
            os.system(
                f"ffmpeg -i {self.root_path}/uploads/{filename} -ss 00:00:00.000 -vframes 1 {self.root_path}/thumbnails/{filename}.webp")

    def add_user(self, username, password, registered=True):
        self.conn.send({'msg': 'add_user', 'username': username, 'password': password, 'registered': registered})

    def get_user(self, username):
        self.conn.send({'msg': 'get_user', 'username': username})
        return self.conn.recv()

    def send_rating(self, item, rating, username):
        self.conn.send({'msg': 'send_rating', 'username': username, 'item': item, 'rating': rating})

    def get_top_n(self, username, n=10):
        self.conn.send({'msg': 'get_top_n', 'username': username, "n": n})
        return self.conn.recv()

    def get_pic(self, item):
        self.conn.send({'msg': 'get_pic', 'item': item})
        return self.conn.recv()

    def send_pic(self, stream, username, file_extension, title, show_username):
        if file_extension in ALLOWED_EXTENSIONS:
            filename = generate_unique_filename(self.root_path + "/uploads/")
            full_filename = f"{filename}.{file_extension}"
            with open(self.root_path + "/uploads/" + full_filename, 'wb') as f:
                shutil.copyfileobj(stream, f)
            if file_extension == "webm" or file_extension == "mp4":
                self.create_thumbnail(filename)

            self.conn.send({'msg': 'send_pic', 'filename': full_filename, 'username': username, "title": title,
                            "show_username": show_username})

    def get_upload_overview(self, username):
        self.conn.send({'msg': 'get_upload_overview', 'username': username})
        return self.conn.recv()

    def merge_user(self, new_username, password, old_username):
        self.conn.send(
            {'msg': 'merge_user', 'username': new_username, 'password': password, 'old_username': old_username})

    def tear_down_connection(self):
        self.conn.close()

# address = ('localhost', 6000)
# conn = Client(address, authkey=b'secret password')


# can also send arbitrary objects:
# conn.send(['a', 2.5, None, int, sum])
# conn.close()
