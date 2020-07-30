from multiprocessing.connection import Client
import time

address = ('localhost', 6000)
conn = Client(address, authkey=b'secret password')
conn.send({'msg' : 'save'})
conn.close()