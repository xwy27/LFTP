import RDP
import utils
import sys
import time
import threading

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
  while True:
    # If exit command is given
    if exit:
      # If no more threads excepts console() and listen()
      # is active, stop listen()
      if threading.active_count() == 2:
        # TODO: Stop listen() here
        break
      else:
        time.sleep(0.5)
        continue
    

# Write a file whose name is filename of length
# Can not happen while others' reading and writing the same file
def writeFile(filename, length):
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

  # TODO: Write file here
  
  # End of writing
  wLockDict[filename].release()  


# Readfile whose name is filename
# Can only be running after current writing finished
# Can read files being read by others
def readFile(filename):
  global wLockDict
  global rLockDict
  global rCountDict

  # TODO: Check if the file exists

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
  
  # TODO: Read file here

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