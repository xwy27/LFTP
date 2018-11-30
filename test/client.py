import sys
sys.path.append("../code")
from rdp import *

client = RDP(client=True)
client.makeConnection(addr='localhost', port=8080)
new_client = RDP(client=True)
new_client.makeConnection(addr='localhost', port=8080)

client.rdp_send('HI, here is client')
new_client.rdp_send('HI, here is new_client')