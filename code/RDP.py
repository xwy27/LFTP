class Flag():
  '''
  Flag field for packet header
  '''
  def __init__(self, ACK = False, RST = False, SYN = False, FIN = False):
    self.ACK = ACK
    self.RST = RST
    self.SYN = SYN
    self.FIN = FIN

class packet_header():
  '''
  Packet header
  '''
  def __init__(self, srcPort = 0, dstPort = 0, SeqNum = 0, ACKNum = 0,
    Flag = Flag(), rwnd = 0, checksum = 0):
    self.srcPort = srcPort
    self.dstPort = dstPort
    self.SeqNum = SeqNum
    self.ACKNum = ACKNum
    self.Flag = Flag
    self.rwnd = rwnd
    self.checksum = checksum

class packet():
  '''
  Packet
  '''
  def __init__(self, packet_header, data):
    self.packet_header = packet_header
    self.data = data

class RDP():
  '''
  RDP Protocol
  '''
  def bindPort(self, port):
    '''
    Bind the port for RDP
    '''
    pass

  def send(self, data, addr):
    '''
    Retrieve data from application layer and send to addr
    '''
    pass

  def get(self, file, addr):
    '''
    Send file from addr to application layer
    '''
    pass

  def rdp_send(self, data, addr):
    '''
    Send data to destination with rdp protocol
    '''
    pass
  