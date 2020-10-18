import json
from multiprocessing.connection import Client
import time

from util import load_config

address = ('localhost', 6000)
conn = Client(address, authkey=load_config()["database"]["password"].decode())
conn.send({'msg' : 'save'})
conn.close()