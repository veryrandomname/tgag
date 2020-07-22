from multiprocessing.connection import Client
import time

address = ('localhost', 6000)
conn = Client(address, authkey=b'secret password')


def add_user(username,password):
    conn.send({'msg': 'add_user', 'username' : username, 'password' : password})

def get_user(username):
    conn.send({'msg': 'get_user', 'username' : username})
    return conn.recv()

def send_rating(item, username, rating):
    conn.send({'msg': 'send_rating', 'username' : username, 'item' : item, 'rating' : rating})

def get_top_n(item,username,n=10):
    conn.send({'msg': 'get_top_n', 'username' : username})
    return conn.recv()

def get_pic(item):
    conn.send({'msg': 'get_pic', 'item' : item})
    return conn.recv()

def send_pic(filename):
    conn.send({'msg': 'send_pic', 'filename' : filename})


def tear_down_connection():
    conn.close()

# can also send arbitrary objects:
# conn.send(['a', 2.5, None, int, sum])
#conn.close()