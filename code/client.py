# -*- coding:utf-8 -*-
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
    
    print("making connection")
    if not client.makeConnection(addr=hostname, port=port):
      print("Error while connecting server.")
      return
    
    print("sending command")
    if not client.rdp_send("lsend\n" + filename + "\n" + str(length)):
      print("Error while sending command.")
      return

    print("waiting for response")
    response = client.rdp_recv(1024)
    if response != "OK":
      print("Error while waiting for response! " + response)
      return

    print("start delivery")
    start_time = time.time()
    DIV_SIZE = int(60000 / 4 * 3)
    SECTION_NUM = 5
    while sentLength != length:
      line = ''
      metaLine = f.read(DIV_SIZE * SECTION_NUM)
      for x in range(0, SECTION_NUM):
        line += base64.b64encode(metaLine[x * DIV_SIZE:x * DIV_SIZE + DIV_SIZE]).decode("ASCII")
      if not client.rdp_send(line):
        print("Error while sending file %s." % filename)
        return
      sentLength += len(metaLine)
      print("Sent:  %d bytes" % sentLength)
      print("Total: %d bytes" % length)
      print("Sending file %s: %d%% done." % (filename, sentLength / length * 100))
      print("Speed: %d KB/second" % (sentLength / (time.time() - start_time + 0.01) / 1000))
    print("Sending done.")

def lGet():
  filename = sys.argv[3]

  # Handle hostname and port
  serverPath = sys.argv[2].split(":")
  hostname = serverPath[0]
  if len(serverPath) == 2:
    port = int(serverPath[1])
  else:
    port = 8080
  
  with open(sys.argv[3], "wb") as f:
    client = RDP.RDP(client=True)

    if not client.makeConnection(addr=hostname, port=port):
      print("Error while connecting server.")
      return
    
    if not client.rdp_send("lget\n" + filename):
      print("Error while sending command.")
      return
    
    response = client.rdp_recv(1024)
    if response == "NO":
      print("No Such File")
      return
    elif response == "":
      print("Error while waiting for response!")
      return
    
    response = response.split("\n")
    print("Response from server: ", "".join(response))
    if response[0] != "OK" or len(response) != 2:
      print("Error while analysising response!")
      return
    
    length = int(response[1])
    acLength = 0
    start_time = time.time()
    while True:
      if acLength == length:
        print("Receiving %s: Done" % filename)
        break
      # Receive some data
      metadata = client.rdp_recv(60000)
      print("Received Length: ", len(metadata))
      data = base64.b64decode(metadata.encode("ASCII"))
      if len(data) == 0:
        print("Receiving %s: Connection Error: Timeout when receiving data." % filename)
        break
      acLength += len(data)
      print("Recv:  %d bytes" % acLength)
      print("Total: %d bytes" % length)
      print("Receiving %s: %d%% data received..." % (filename, acLength / length * 100))
      print("Speed: %d KB/s" % (acLength / (time.time() - start_time + 0.01) / 1000))
      # Write to file
      f.write(data)

if not os.path.exists('data'):
  os.makedirs('data')

if len(sys.argv) != 4:
  print("Invalid arguments.")
  print("Usage:")
  print("  python client.py lsend/lget hostname[:port] filename")
else:
  if sys.argv[1] == "lsend":
    lSend()
  elif sys.argv[1] == "lget":
    lGet()
  else:
    print("Invalid arguments.")
    print("Usage:")
    print("  python client.py lsend/lget hostname[:port] filename")