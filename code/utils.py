import socket

def getPort():
  '''
  Find an avaliable port num from 60000 to 10000 in localhost
  '''
  for port in range(60000, 10000, -1):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ans = sock.connect_ex(('localhost', port))
    sock.close()
    if ans:
      continue
    else:
      return port
