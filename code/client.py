import RDP
import sys
import os
import os.path
import base64
import time

def lSend():
  # Check if file exists
  if not os.path.exists(sys.argv[3]):
    print("Error: No such file.")
    return

  filename = os.path.basename(sys.argv[3])
  
  # Get the length of file and the file itself
  length = os.stat(sys.argv[3]).st_size
  sentLength = 0

  # Handle hostname and port
  serverPath = sys.argv[2].split(":")
  hostname = serverPath[0]
  if len(serverPath) == 2:
    port = int(serverPath[1])
  else:
    port = 8080
  
  # Handle file
  with open(sys.argv[3], "rb") as f:
    client = RDP.RDP(client=True)
    
    if not client.makeConnection(addr=hostname, port=port):
      print("Error while connecting server.")
      return
    
    if not client.rdp_send("lsend\n" + filename + "\n" + str(length)):
      print("Error while sending command.")
      return

    response = client.rdp_recv(1024)
    if response != "OK":
      print("Error while waiting for response! " + response)
      return

    while sentLength != length:
      line = f.read(10240)
      if not client.rdp_send(base64.b64encode(line).decode("ASCII")):
        print("Error while sending file %s." % filename)
        return
      sentLength += len(line)
      print("Sending file %s: %d%% done." % (filename, sentLength / length * 100))
    print("Sending done.")

def lGet():
  pass

if len(sys.argv) != 4:
  print("Invalid arguments.")
  print("Usage:")
  print("  python client.py lsend/lget hostname[:port] filename")
else:
  if sys.argv[1] == "lsend":
    lSend()
  elif sys.argv[1] == "lget":
    pass
  else:
    print("Invalid arguments.")
    print("Usage:")
    print("  python client.py lsend/lget hostname[:port] filename")