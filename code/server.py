from rdp import *
import sys
import time
import threading

exit = False

def threadTest():
  global exit
  while True:
    if exit :
      print("Thread %s exit" % threading.current_thread().name)
      return
    print("Testing thread %s: running" % threading.current_thread().name)
    time.sleep(0.5)

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
    elif command == "createThread":
      thread = threading.Thread(target=threadTest, name="Thread " + str(threading.active_count()))
      thread.start()
    else:
      print("Invalid input.")


# Check if Arguments are valid
if len(sys.argv) == 2 and sys.argv[1] == "help":
  print("Usage:")
  print("  python server.py [hostname port]")
elif len(sys.argv) == 3:
  hostname = sys.argv[1]
  port = sys.argv[2]
  print("Start listening at %s:%s-*" % (hostname, port))
  console()
elif len(sys.argv) == 1:
  hostname = "localhost"
  port = "8080"
  print("Start listening at localhost:8080")
  console()
else:
  print("Invalid input!")
  print("Usage:")
  print("  python server.py [hostname] [port]")