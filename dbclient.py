from multiprocessing.connection import Client
import time

address = ('localhost', 6000)
conn = Client(address, authkey=b'secret password')


def add_user(username,password):
    conn.send({'msg': 'add_user', 'username' : username, 'password' : password})

def get_user(username):
    conn.send({'msg': 'get_user', 'username' : username})
    return conn.recv()

def send_like(username, like):
    conn.send({'msg': 'send_like', 'username' : username, 'like' : like})

def get_top

def tear_down_connection():
    conn.close()

# can also send arbitrary objects:
# conn.send(['a', 2.5, None, int, sum])
#conn.close()