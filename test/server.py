# -*- coding:utf-8 -*-
from rdp import *
import sys
import threading
sys.path.append("../code")

server = RDP(port=8080)
num = 2
# shakeTheard = threading.Thread(target=server.listen, args=(num,), name='handshake')
# shakeTheard.start()


server.listen(1)

connSocket = server.accept()
while connSocket == None:
    connSocket = server.accept()

print('Online')
while True:
    data = connSocket.rdp_recv(1024)
    print(data)
