import RDP
import sys
import os
import os.path

if len(sys.argv) != 4:
  print("Invalid arguments.")
  print("Usage:")
  print("  python client.py lsend/lget hostname[:port] filename")
else:
  if sys.argv[1] == "lsend":
    pass
  elif sys.argv[1] == "lget":
    pass
  else:
    print("Invalid arguments.")
    print("Usage:")
    print("  python client.py lsend/lget hostname[:port] filename")

def lSend():
  # Check if file exists
  if not os.path.exists(sys.argv[3]):
    print("Error: No such file.")
    return
  
  # Get the length of file and the file itself
  length = os.stat(sys.argv[3]).st_size
  serverPath = sys.argv[3].split(":")
  hostname = serverPath[0]
  if len(serverPath) == 2:
    port = int(serverPath[1])
  else:
    port = 8080
  with open(sys.argv[3], "rb") as f:
    client = RDP.RDP(client=True)
    client.makeConnection(addr=hostname, port=port)
    for line in f:

  

def lGet():
  pass