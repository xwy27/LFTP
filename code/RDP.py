# TODO: decode data received from bytes to str and recover into packet
import socket
import random

import utils

class Flag():
  '''
  Flag field(ACK, RST, SYN, FIN) for packet header
  '''
  def __init__(self, ACK = False, RST = False, SYN = False, FIN = False):
    self.ACK = ACK
    self.RST = RST
    self.SYN = SYN
    self.FIN = FIN
  
  def __str__(self):
    return (str(self.ACK) + str(self.SYN) + str(self.FIN) + str(self.RST))

  def getStr(self):
    return self.__str__()

class packet_header():
  '''
  Packet header with srcPort, dstPort, SequenceNumber, ACKNumber,
  FlagField(ACK, RST, SYN, FIN), rwnd and CheckSum
  '''
  def __init__(self, SeqNum = 0, ACKNum = 0, Flag = Flag(), rwnd = 0, checksum = 0):
    self.SeqNum = SeqNum
    self.ACKNum = ACKNum
    self.Flag = Flag
    self.rwnd = rwnd
    self.checksum = checksum
  
  def __str__(self):
    return (str(self.SeqNum) + str(self.ACKNum) + self.Flag.getStr() +
      str(self.rwnd) + str(self.checksum))
  
  def getStr(self):
    return self.__str__()

class packet():
  '''
  Packet with packet_header and data
  '''
  def __init__(self, packet_header, data):
    self.packet_header = packet_header
    self.data = data
  
  def __str__(self):
    return (self.packet_header.getStr() + str(self.data))
  
  def getStr(self):
    return self.__str__()

class RDP():
  '''
  Create a socket running RDP at addr:port
  '''
  def __init__(self, addr="localhost", port=10000):
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.localAddr = (addr, port)
    self.sock.bind(self.localAddr)  # Bind local addr for sock
    self.sock.settimeout(2) # set timeout seconds
    print('RDP running on %s:%s' %self.localAddr)
    
    self.csAddr = ('', 0) # Bind client or server address
    self.clientSock = []  # Activate sockets for server to serve client

  def rdp_send(self, data):
    '''
    Send a data string to the socket.
    Return the number of bytes sent;
    this may be less than len(data) if the network is busy.
    '''
    pass
    return self.sock.send(data)

  def rdp_recv(self, bufferSize):
    '''
    Receive up to buffersize bytes from the socket.
    When no data is available, block until at least one byte is available
    or until the remote end is closed.
    When the remote end is closed and all data is read, return the empty string.
    '''
    pass
    return self.sock.recv(bufferSize)

  def makeConnection(self, addr, port):
    # Send SYN Packet
    print('Start handshake with server(%s:%s)' %(addr, port))
    flag = Flag(SYN=True)
    seq = random.randint(1, 10)
    header = packet_header(SeqNum=seq, Flag=flag)
    pkt = packet(header, '')
    self.sock.sendto(pkt.getStr().encode(), (addr, port))
    
    cnt = 0
    while True:
      # Wait ACK Packet
      try:
        data, rcv_addr = self.sock.recvfrom(1024)
      except:
        # No confirm SYN packet, resend SYN
        if cnt < 5:
          print('Timeout for receiving ACK from server(%s:%s)...\nResending...' %(addr, port))
          pkt = packet(header, '')
          self.sock.sendto(pkt.getStr().encode(), (addr, port))
          cnt += 1
        else:
          print('ERROR:\nHandshake with server(%s:%s) failed with server ERROR!' %(addr, port))
          break

      if (rcv_addr != (addr, port) or\
        not data.packet_header.Flag.ACK or\
        data.packet_header.ACK != seq):
        continue
      
      # ACK received, send ACK Packet
      new_port = data.data
      flag = Flag(ACK=True)
      seq = seq + 1
      header = packet_header(SeqNum=seq, ACKNum=data.packet_header.SeqNum, Flag=flag)
      pkt = packet(header, '')
      self.sock.sendto(pkt.getStr().encode(), (addr, port))
      # Handshake finish
      self.csAddr = (addr, new_port)
      print('Handshake with server(%s:%s) successfully!' %self.csAddr)
      break

  def listen(self, num):
    self.seq = {}
    self.cnt = 0
    while True:
      if (self.cnt < num):
        try:
          data, rcv_addr = self.sock.recvfrom(1024)
          # SYN Connect Request, send ACK and wait
          if (data.packet_header.Flag.SYN):
            flag = Flag(ACK=True)
            self.seq[rcv_addr] = random.randint(1, 10)
            header = packet_header(SeqNum=self.seq[rcv_addr], ACKNum=data.packet_header.SeqNum, Flag=flag)
            pkt = packet(header, '')
            self.sock.sendto(pkt.getStr().encode(), rcv_addr)
          # ACK receive, check if sent SYN
          if (data.packet_header.Flag.ACK and rcv_addr in self.seq and\
            data.packet_header.ACKNum == self.seq[rcv_addr]):
            self.cnt += 1
            new_port = utils.getPort()
            self.clientSock.append([rcv_addr, RDP(port=(new_port+random.randint(1,1000)))])
        except:
          continue

  def accept(self):
    self.cnt -= 1
    temp = self.clientSock.pop()
    del self.seq[temp[0]]
    return temp[1]