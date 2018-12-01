# -*- coding:utf-8 -*-
from rdp import *
import sys
sys.path.append("../code")

client = RDP(client=True)
client.makeConnection(addr='localhost', port=8080)
new_client = RDP(client=True)
new_client.makeConnection(addr='localhost', port=8080)

client.rdp_send('HI, here is client')
new_client.rdp_send('HI, here is new_client')
