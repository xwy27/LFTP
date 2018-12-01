# -*- coding:utf-8 -*-
import utils


class Flag():
    '''
    Flag field(ACK, RST, SYN, FIN) for packet header
    '''

    def __init__(self, ACK=0, RST=0, SYN=0, FIN=0):
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

    def __init__(self, SeqNum=0, ACKNum=0, Flag=Flag(), rwnd=0):
        self.SeqNum = SeqNum
        self.ACKNum = ACKNum
        self.Flag = Flag
        self.rwnd = rwnd

    def __str__(self):
        return (str(self.SeqNum) + utils.delimeter + str(self.ACKNum) + utils.delimeter +
                self.Flag.getStr() + utils.delimeter + str(self.rwnd))

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
