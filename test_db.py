from multiprocessing.connection import Client
import time

address = ('localhost', 6000)
conn = Client(address, authkey=b'secret password')
for i in range(10):
    time.sleep(3)
    conn.send(i)
    print("send " + str(i))
conn.send('close')

# can also send arbitrary objects:
# conn.send(['a', 2.5, None, int, sum])
#conn.close()