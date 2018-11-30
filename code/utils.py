import socket
import random

delimeter = '$'

def getPort():
  '''
  Find an avaliable port num from 60000 to 10000 in localhost
  '''
  def isPortFree(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  while True:
    port = random.randint(30000, 60000)
    try:
      sock.bind(('127.0.0.1', port))
    except(e):
      sock.close()
      # print(e)
      continue
    sock.close()
    return port
