# -*- coding:utf-8 -*- 
import socket
import random
import enum

import utils

class Flag():
  '''
  Flag field(ACK, RST, SYN, FIN) for packet header
  '''
  def __init__(self, ACK = 0, RST = 0, SYN = 0, FIN = 0):
    self.ACK = ACK
    self.RST = RST
    self.SYN = SYN
    self.FIN = FIN
  
  def __str__(self):
    return (str(self.ACK) + utils.delimeter + str(self.SYN) +
      utils.delimeter + str(self.FIN) + utils.delimeter + str(self.RST))

  def getStr(self):
    return self.__str__()

class packet_header():
  '''
  Packet header with srcPort, dstPort, SequenceNumber, ACKNumber,
  FlagField(ACK, RST, SYN, FIN), rwnd
  '''
  def __init__(self, SeqNum = 0, ACKNum = 0, Flag = Flag(), rwnd = 0):
    self.SeqNum = SeqNum
    self.ACKNum = ACKNum
    self.Flag = Flag
    self.rwnd = rwnd
  
  def __str__(self):
    return (str(self.SeqNum) + utils.delimeter + str(self.ACKNum) + utils.delimeter +
      self.Flag.getStr() + utils.delimeter +  str(self.rwnd))
  
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
    return (self.packet_header.getStr() + utils.delimeter + str(self.data))
  
  def getStr(self):
    return self.__str__()

class RDP():
  '''
  Create a socket running RDP at addr:port
  '''
  def __init__(self, addr='localhost', port=10000, client=False):
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if not client:
      self.sock.bind((addr, port))  # Bind local addr for sock
      print('Server RDP running on %s:%s' %self.sock.getsockname())
    else:
      print('Client RDP running')
    self.csAddr = ('', 0) # Bind client or server address
    self.sock.settimeout(1) # set timeout seconds
    
    self.MSS = 2 # Max Sending Size
    self.windowSize = 4 # max size of the sending/receiving window
    # self.lastAck = 0  # for sender to check the last ack packet in pipline
    # self.lastSend = 0 # for sender to check the last send packet in pipline
    self.rcv_base = 0 # for receiver to check the hoping receive pkt

    self.clientSock = []  # Activate sockets for server to serve client

  def rdp_send(self, data):
    '''
    Send a data string to the socket.
    Return true if sent successfully, otherwise false;
    this may be less than len(data) if the network is busy.
    '''
    print('\n')
    print('-'*15,' BEGIN SEND ','-'*15)

    # Split the data
    data_packets = [data[x*self.MSS:x*self.MSS+self.MSS] for x in range(int(len(data)/self.MSS)+1)]

    lastAck = 0  # for sender to check the last ack packet in pipline
    lastSend = 0 # for sender to check the last send packet in pipline
    origin_seq = 0
    total_pkt = len(data_packets) # Total num of data packets to send
    window = [0] * self.windowSize # Sender window
    while lastSend < total_pkt and lastSend - lastAck < self.windowSize:
      seqNum = origin_seq + self.MSS * lastSend
      print('SEND: Begin sending Fragment-%d(SeqNum:%d)...' %(lastSend, seqNum))
      header = packet_header(SeqNum=seqNum, Flag=Flag())
      pkt = packet(packet_header=header, data=data_packets[lastSend])
      self.sock.sendto(pkt.getStr().encode(), self.csAddr)
      lastSend += 1

    timeout_cnt = 0
    while True:
      try:
        rcv_data, rcv_addr = self.sock.recvfrom(1024)
      except:
        # No ACK packet, resend fragment
        if timeout_cnt < 5:
          print('SEND: Timeout for receiving ACK from(%s:%s)...' %self.csAddr)
          for index, win in enumerate(window):
            if not int(win):
              pkt_index = index + lastAck
              print('SEND: Resending fragment-%d ...' %pkt_index)
              seqNum = origin_seq + self.MSS * pkt_index
              header = packet_header(SeqNum=seqNum, Flag=Flag())
              pkt = packet(packet_header=header, data=data_packets[pkt_index])
              self.sock.sendto(pkt.getStr().encode(), self.csAddr)
          timeout_cnt += 1
          continue
        else:
          print('SEND: ERROR: (%s:%s) offline, sending data failed!' %(self.csAddr))
          return False

      # Check if ACK packet
      decode_data = rcv_data.decode()
      decode_ack = decode_data.split('$')[2]
      decode_ackNum = decode_data.split('$')[1]
      if (int(decode_ack)):
        ack_index = int((int(decode_ackNum) - origin_seq)/self.MSS)
        window_index = int((int(decode_ackNum) - origin_seq - lastAck*self.MSS)/self.MSS)
        # print('SEND: ACK pkt(ACKNum:%d, windowIndex:%d, lastACK:%d, lastSend:%d)' %(int(decode_ackNum), ack_index, lastAck, lastSend))
        if (ack_index > lastAck and ack_index < lastSend):
          window[window_index] = 1
          print('SEND: Fragment-%d sends successfully!(Waiting to move window...)' %ack_index)
        elif (ack_index == lastAck):
          print('SEND: Fragment-%d sends successfully!' %ack_index)
          window[window_index] = 1
          for w in window:
            if int(w):
              lastAck += 1
              w = 0
            else:
              break
          while lastSend < total_pkt and lastSend - lastAck < self.windowSize:
            seqNum = origin_seq + self.MSS * lastSend
            print('SEND: Begin sending Fragment-%d(SeqNum:%d)...' %(lastSend, seqNum))
            header = packet_header(SeqNum=seqNum, Flag=Flag())
            pkt = packet(packet_header=header, data=data_packets[lastSend])
            self.sock.sendto(pkt.getStr().encode(), self.csAddr)
            lastSend += 1
        if lastAck == total_pkt - 1:
          print('SEND: Data sends successfully')
          print('-'*15,' END SEND ','-'*15, '\n')
          return True

    print('SEND: Something WRONG, try agin...')
    print('-'*15,' END SEND ','-'*15, '\n')
    return False

  def rdp_recv(self, bufferSize):
    '''
    Receive up to buffersize bytes from the socket.
    When no data is available, block until at least one byte is available
    or until the remote end is closed.
    When the remote end is closed and all data is read, return the empty string.
    '''
    data = ''
    window = [[0, ''] * self.windowSize]
    cnt = 0
    ack_cnt = 0
    flag = Flag(ACK=1)
    origin_seq = random.randint(1,10)
    while len(data) < bufferSize:
      try:
        rcv_data, rcv_addr = self.sock.recvfrom(1024)
      except:
        if cnt < 3:
          print('RECV: Waiting packets from (%s:%s)...' %self.csAddr)
          cnt += 1
          continue
        else:
          print('RECV: No data received from (%s:%s). Finish' %(self.csAddr))
          return data
      
      if (rcv_addr == self.csAddr): # From client/server pkt
        decode_data = rcv_data.decode()
        decode_seqNum = int(decode_data.split('$')[0])
        back_ack = self.rcv_base - self.windowSize * self.MSS
        if (back_ack >= 0 and decode_seqNum < self.rcv_base and back_ack >= decode_seqNum):
          # [rcv_base-N, rcv_bace) pkt, resend ACK in case sender repeat resending
          print('RECV: Before window pkt, resend ack...')
          header = packet_header(SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=flag)
          pkt = packet(header, '')
          self.sock.sendto(pkt.getStr().encode(), self.csAddr)
          ack_cnt += 1
        elif (decode_seqNum > self.rcv_base and decode_seqNum <= self.rcv_base+(self.windowSize-1)*self.MSS):
          # (rcv_base, rcv_base+(N-1)*MSS] pkt, buffer pkt
          print('RECV: Inside window pkt(SeqNum:%d), buffer data' %decode_seqNum)
          seq_index = int((decode_seqNum - self.rcv_base)/self.MSS)
          
          # Buffer data
          window[seq_index][0] = 1
          temp = ''
          for index, val in enumerate(decode_data.split('$')[utils.data_index:]):
            if (index == 0):
              temp += val
            else:
              temp = temp + '$' + val
          window[seq_index][1] = temp

          # ACK data
          header = packet_header(SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=flag)
          pkt = packet(header, '')
          self.sock.sendto(pkt.getStr().encode(), self.csAddr)
          ack_cnt += 1
        
        if decode_seqNum == self.rcv_base:
          print('RECV: Window start pkt(SeqNum:%d), return continual data' %decode_seqNum)
          header = packet_header(SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=flag)
          pkt = packet(header, '')
          self.sock.sendto(pkt.getStr().encode(), self.csAddr)
          ack_cnt += 1

          # Set data for rcv_base
          seq_index = int((decode_seqNum - self.rcv_base)/self.MSS)
          window[seq_index][0] = 1
          temp = ''
          for index, val in enumerate(decode_data.split('$')[utils.data_index:]):
            if (index == 0):
              temp += val
            else:
              temp = temp + '$' + val
          window[seq_index][1] = temp
          
          # Return continual data
          for w in window:
            if int(w[0]):
              data += w[1]
              self.rcv_base += self.MSS
              w[0] = 0
              w[1] = ''
            else:
              break
          return data    
    return data

  def makeConnection(self, addr, port):
    addr = '127.0.0.1' if (addr == 'localhost') else addr
    # Send SYN Packet
    print('CONNECT: Start handshake with server(%s:%s)' %(addr, port))
    flag = Flag(SYN=1)
    seq = random.randint(1, 10)
    header = packet_header(SeqNum=seq, Flag=flag)
    pkt = packet(header, '')
    print('CONNECT: Send SYN to server(%s:%s): %s' %(addr, port, pkt.getStr()))
    self.sock.sendto(pkt.getStr().encode(), (addr, port))

    cnt = 0
    while True:
      # Wait ACK Packet
      try:
        rcv_data, rcv_addr = self.sock.recvfrom(1024)
      except:
        # No confirm SYN packet, resend SYN
        if cnt < 5:
          print('CONNECT: Timeout for receiving ACK from server(%s:%s)...\nResending...' %(addr, port))
          pkt = packet(header, '')
          self.sock.sendto(pkt.getStr().encode(), (addr, port))
          cnt += 1
          continue
        else:
          print('CONNECT: ERROR:\nHandshake with server(%s:%s) failed with server ERROR!' %(addr, port))
          break
        
      # rcv_data, rcv_addr = self.sock.recvfrom(1024)
      data = rcv_data.decode()
      print('CONNECT: Packet from (%s): %s' %(rcv_addr, data))
      decode_ackNum = data.split('$')[1]
      decode_ack = data.split('$')[2]
      # not from server or not ACK or not ACK sent packet seqNum, drop rcv_packet
      if (rcv_addr != (addr, port) or not int(decode_ack) or int(decode_ackNum) != seq):
        continue
      
      # ACK received, send ACK Packet
      new_port = data.split('$')[-1]
      flag = Flag(ACK=1)
      seq = seq + 1
      decode_seqNum = data.split('$')[0]
      header = packet_header(SeqNum=seq, ACKNum=decode_seqNum, Flag=flag)
      pkt = packet(header, '')
      print('CONNECT: ACK confirmed, send ACK to server(%s): %s' %(rcv_addr, pkt.getStr()))
      self.sock.sendto(pkt.getStr().encode(), (addr, port))
      # Handshake finish
      self.csAddr = (addr, int(new_port))
      print('CONNECT: Handshake with server(%s:%s) successfully!' %self.csAddr)
      break

  def listen(self, num):
    '''
    Listen the server port and wait for handshake client;
    Max successful handshake client number is num
    '''
    self.seq = {}
    self.cnt = 0
    # self.clientPort = {}
    self.new_port = {}
    while True:
      try:
        rcv_data, rcv_addr = self.sock.recvfrom(1024)
      except:
        continue

      if (self.cnt < num):
        data = rcv_data.decode()
        decode_syn = data.split('$')[3]
        decode_ack = data.split('$')[2]
        # SYN Connect Request, send ACK and wait
        decode_seqNum = int(data.split('$')[0])
        if (int(decode_syn)):
          if (rcv_addr in self.new_port):
            continue  
          flag = Flag(ACK=1)
          self.seq[rcv_addr] = random.randint(1, 10)
          print('LISTEN: SYN from client(%s): %s' %(rcv_addr, data))
          self.new_port[rcv_addr] = utils.getPort()
          header = packet_header(SeqNum=self.seq[rcv_addr], ACKNum=decode_seqNum, Flag=flag) 
          pkt = packet(header, self.new_port[rcv_addr])
          print('LISTEN: ACK to client(%s): %s' %(rcv_addr, pkt.getStr()))
          self.sock.sendto(pkt.getStr().encode(), rcv_addr)
        # ACK receive, check if sent SYN
        decode_ackNum = data.split('$')[1]
        print('LISTEN: ACK from client(%s): %s' %(rcv_addr, data))
        
        if (int(decode_ack) and rcv_addr in self.seq and
          int(decode_ackNum) == self.seq[rcv_addr]):
          self.cnt += 1
          print('LISTEN: Handshake finish with client(%s): %s' %(rcv_addr, data))
          self.clientSock.append([rcv_addr, RDP(port=(self.new_port[rcv_addr]))])
          # print('Ports for handshake client:', self.clientSock)
      else:
        break
        print('LISTEN: Serving MAX Client. New Client(%s:%s) request abandoned', rcv_addr)

  def accept(self):
    '''
    Retrieve a client-connected RDP
    '''
    if (len(self.clientSock) > 0):
      self.cnt -= 1
      temp = self.clientSock.pop()
      del self.seq[temp[0]]
      temp[1].csAddr = temp[0]  # set client addr
      return temp[1]
    return None

  def release(self):
    '''
    Cancel a client-connected RDP
    '''
    self.sock.close()
  
  def getLocalAddr(self):
    '''
    Return the RDP running local address in a pair (addr, port)
    '''
    return self.sock.getsockname()