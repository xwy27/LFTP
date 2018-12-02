import RDP
import sys
import time
import threading
import os.path

# Flag to check if the program is going to exit
exit = False

# dictionary: filename => lock
dictLock = threading.Lock()
wLockDict = {}
rLockDict = {}
# current readers' count
rCountDict = {}

# def threadTest():
#   global exit
#   while True:
#     if exit :
#       print("Thread %s exit" % threading.current_thread().name)
#       return
#     print("Testing thread %s: running" % threading.current_thread().name)
#     time.sleep(0.5)

# Console function
# Handle users' input
def console():
  global exit
  while True:
    command = input("$ ")
    if command == "exit":
      exit = True
      while threading.active_count() != 1:
        print("Waiting for %d threads to ends." % (threading.active_count() - 1))
        time.sleep(0.5)
      print("Thanks for your using.")
      break
    elif command != "":
      print("Invalid input.")

def listen(hostname, port):
  server = RDP.RDP(addr=hostname, port=port)
  listenThread = threading.Thread(target=server.listen, args=(10,), name="basic listening")
  listenThread.start()
  while True:
    # If the user is trying to exit
    if exit:
      # Stop the listen thread
      RDP.RDP.exit = True
      if threading.active_count() == 2:
        break
      else:
        time.sleep(0.5)
        continue
    
    clientSocket = server.accept()
    if clientSocket != None:
      threading.Thread(target=handleSocket, args=(clientSocket,))

# Function to handle the session with a client
def handleSocket(socket):
  commandPacket = socket.rdp_recv(1024)
  print("Command received " + commandPacket)
  commandPacket = commandPacket.split("\n")
  if commandPacket[0] == "lget":
    # Sending file
    if len(commandPacket) == 3:
      writeFile(commandPacket[1], int(commandPacket[2]), socket)
    releaseSocket(socket)
  elif commandPacket[0] == "lsend":
    # Getting file
    pass
  else:
    return

def releaseSocket(socket):
  pass

# Write a file whose name is filename of length
# Can not happen while others' reading and writing the same file
def writeFile(filename, length, socket):
  global wLockDict
  global rLockDict
  global rCountDict

  dictLock.acquire()
  # Try to get the writer lock
  if filename not in wLockDict:
    # If no lock is initialized, create one
    wLockDict[filename] = threading.Lock()
    # Get the writer lock
    wLockDict[filename].acquire()
    rLockDict[filename] = threading.Lock()
    rCountDict[filename] = 0
    dictLock.release()
  else:
    dictLock.release()
    # Get the writer lock
    wLockDict[filename].acquire()
    while rLockDict[filename] != 0:
      time.sleep(0.5)

  # Tell client to send file
  if not socket.rdp_send("OK"):
    print("Connection Error: Fail when asking client to send file.")
    wLockDict[filename].release()
    return 
    
  # Accepted Length
  acLength = 0

  with open(filename, "wb") as f:
    while True:
      # User want to exit
      if exit:
        print("Server is exiting...")
        break
      # Finish
      if acLength == length:
        socket.rdp_send("OK")
        print("Receiving %s: Done" % filename)
        break
      # Receive some data
      data = socket.rdp_recv(1024)
      socket.resetRecv()
      if len(data) == 0:
        print("Connection Error: Timeout when receiving data.")
        break
      acLength += len(data)
      print("Receiving %s: %d%% data received..." % (filename, acLength / length * 100))
      # Write to file
      f.write(data)
  
  # End of writing
  wLockDict[filename].release()  


# Readfile whose name is filename
# Can only be running after current writing finished
# Can read files being read by others
def readFile(filename, socket):
  global wLockDict
  global rLockDict
  global rCountDict

  if not os.path.exists(filename):
    socket.rdp_send("Error: File Not Existed!")
    return

  dictLock.acquire()
  if filename not in wLockDict:
    # If no lock is initialized, create one
    wLockDict[filename] = threading.Lock()
    # Get the writer lock
    wLockDict[filename].acquire()
    rLockDict[filename] = threading.Lock()
    rLockDict[filename].acquire()
    rCountDict[filename] = 1
    wLockDict[filename].release()
    dictLock.release()
  else:
    dictLock.release()
    wLockDict[filename].acquire()
    rLockDict[filename].acquire()
    rCountDict[filename] += 1
    rLockDict[filename].release()
    wLockDict[filename].release()
  
  

  rLockDict[filename].acquire()
  rCountDict[filename] -= 1
  rLockDict[filename].release()





# Check if Arguments are valid
if len(sys.argv) == 2 and sys.argv[1] == "help":
  print("Usage:")
  print("  python server.py [hostname port]")
elif len(sys.argv) == 3:
  hostname = sys.argv[1]
  port = sys.argv[2]
  print("Start listening at %s:%s-*" % (hostname, port))
  listenThread = threading.Thread(target=listen, args=(hostname, port), name="Listen Thread")
  listenThread.start()
  console()
elif len(sys.argv) == 1:
  hostname = "localhost"
  port = "8080"
  print("Start listening at localhost:8080")
  listenThread = threading.Thread(target=listen, args=(hostname, port), name="Listen Thread")
  listenThread.start()
  console()
else:
  print("Invalid input!")
  print("Usage:")
  print("  python server.py [hostname] [port]")