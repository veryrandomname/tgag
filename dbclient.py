from multiprocessing.connection import Client
import time

class MyClient:
    conn = None
    def __init__(self, address=('localhost', 6000), authkey=b'secret password'):
        self.conn = Client(address, authkey=authkey)


    def add_user(self,username,password):
        self.conn.send({'msg': 'add_user', 'username' : username, 'password' : password})

    def get_user(self,username):
        self.conn.send({'msg': 'get_user', 'username' : username})
        return self.conn.recv()

    def send_rating(self,item, rating, username):
        self.conn.send({'msg': 'send_rating', 'username' : username, 'item' : item, 'rating' : rating})

    def get_top_n(self,username,n=10):
        self.conn.send({'msg': 'get_top_n', 'username' : username, "n" : n})
        return self.conn.recv()

    def get_pic(self,item):
        self.conn.send({'msg': 'get_pic', 'item' : item})
        return self.conn.recv()

    def send_pic(self,filename, username):
        self.conn.send({'msg': 'send_pic', 'filename' : filename, 'username' : username})

    def get_upload_overview(self, username):
        self.conn.send({'msg': 'get_upload_overview', 'username' : username})
        return self.conn.recv()

    def tear_down_connection(self):
        self.conn.close()

#address = ('localhost', 6000)
#conn = Client(address, authkey=b'secret password')




# can also send arbitrary objects:
# conn.send(['a', 2.5, None, int, sum])
#conn.close()