# -*- coding:utf-8 -*-
import socket
import random
import enum

import utils
from rdp_header import *


class RDP():
    '''
    Create a socket running RDP at addr:port
    '''

    exit = False

    def __init__(self, addr='localhost', port=10000, client=False):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if not client:
            self.sock.bind((addr, port))  # Bind local addr for sock
            print('Server RDP running on %s:%s' % self.sock.getsockname())
        else:
            print('Client RDP running')
        self.csAddr = ('', 0)  # Bind client or server address
        self.sock.settimeout(1)  # set timeout seconds

        self.MSS = 500  # Max Sending Size
        self.sendWindowSize = 4  # max size of the sending window
        self.recvWindowSize = 4  # max size of the receiving window

        # self.lastAck = 0  # for sender to check the last ack packet in pipline
        # self.lastSend = 0 # for sender to check the last send packet in pipline

        self.rcv_base = 0  # for receiver to check the hoping receive pkt

        # ATTENTION:
        # Once invoked the rdp_recv(bufferSize) function, at most bufferSize data is returned
        # So the lastByteRead is always zero and the len(rcv_buffer) is the lastByteRecv
        # The rwnd = BufferSize - (lastByteRecv - lastByteRead) = BufferSize - len(rcv_buffer)
        self.rcv_buffer = ''  # buffer for rcv_data
        self.rcv_bufferSize = 4096  # buffer size

        self.clientSock = []  # Activate sockets for server to serve client

    def rdp_send(self, data):
        '''
        Send a data string to the socket.
        Return true if sent successfully, otherwise false;
        this may be less than len(data) if the network is busy.
        '''
        print('\n')
        print('-'*15, ' BEGIN SEND ', '-'*15)

        # Split the data
        data_packets = [data[x*self.MSS:x*self.MSS+self.MSS]
                        for x in range(int(len(data)/self.MSS)+1)]

        lastAck = 0  # for sender to check the last ack packet in pipline
        lastSend = 0  # for sender to check the last send packet in pipline
        origin_seq = 0  # origin sequence number
        total_pkt = len(data_packets)  # Total num of data packets to send
        # Sender window, 0 for not ack, 1 for ack
        window = [0] * self.sendWindowSize
        while lastSend < total_pkt and lastSend - lastAck < self.sendWindowSize:
            seqNum = origin_seq + self.MSS * lastSend
            print('SEND: Begin sending Fragment-%d(SeqNum:%d)...' %
                  (lastSend, seqNum))
            header = packet_header(SeqNum=seqNum, Flag=Flag())
            pkt = packet(packet_header=header, data=data_packets[lastSend])
            self.sock.sendto(pkt.getStr().encode(), self.csAddr)
            lastSend += 1

        timeout_cnt = 0  # counter for timeout
        while True:
            if exit: return
            try:
                rcv_data, rcv_addr = self.sock.recvfrom(1024)
            except:
                # No ACK packet, resend fragment
                if timeout_cnt < 5:
                    print('SEND: Timeout for receiving ACK from(%s:%s)...' %
                          self.csAddr)
                    for index, win in enumerate(window):
                        if not int(win):
                            pkt_index = index + lastAck
                            print('SEND: Resending fragment-%d ...' %
                                  pkt_index)
                            seqNum = origin_seq + self.MSS * pkt_index
                            header = packet_header(SeqNum=seqNum, Flag=Flag())
                            pkt = packet(packet_header=header,
                                         data=data_packets[pkt_index])
                            self.sock.sendto(
                                pkt.getStr().encode(), self.csAddr)
                    timeout_cnt += 1
                    continue
                else:
                    print('SEND: ERROR: (%s:%s) offline, sending data failed!' % (
                        self.csAddr))
                    break

            # Check if ACK packet
            decode_data = rcv_data.decode()
            decode_ack = decode_data.split('$')[2]
            decode_ackNum = decode_data.split('$')[1]
            if (int(decode_ack)):
                ack_index = int((int(decode_ackNum) - origin_seq)/self.MSS)
                window_index = int(
                    (int(decode_ackNum) - origin_seq - lastAck*self.MSS)/self.MSS)
                # print('SEND: ACK pkt(ACKNum:%d, windowIndex:%d, lastACK:%d, lastSend:%d)' % (
                #     int(decode_ackNum), ack_index, lastAck, lastSend))
                if (ack_index > lastAck and ack_index < lastSend):
                    decode_rwnd = decode_data.split('$')[7]
                    # Update sending window size
                    self.sendWindowSize = int(decode_rwnd)
                    window[window_index] = 1
                    print(
                        'SEND: Fragment-%d sends successfully!(Waiting to move window...)' % ack_index)
                elif (ack_index == lastAck):
                    print(
                        'SEND: Fragment-%d sends successfully!(Move Window)' % ack_index)
                    decode_rwnd = decode_data.split('$')[7]
                    # Update sending window size
                    self.sendWindowSize = int(decode_rwnd)
                    window[window_index] = 1
                    for w in window:
                        if int(w):
                            lastAck += 1
                            w = 0
                        else:
                            break

                    if self.sendWindowSize == 0:  # Start waiting rwnd
                        print('SEND: Waiting for receiver to have buffer(rwnd)')
                        rwnd_seq = 0
                        while True:
                            rwnd_flag = Flag(WRW=1)
                            rwnd_header = packet_header(
                                SeqNum=rwnd_seq, Flag=rwnd_flag)
                            rwnd_pkt = packet(
                                packet_header=rwnd_header, data='')
                            self.sock.sendto(
                                rwnd_pkt.getStr().encode(), self.csAddr)
                            try:
                                rwnd_data, rwnd_addr = self.sock.recvfrom(1024)
                            except:
                                continue

                            rwnd_decode_data = rwnd_data.decode()
                            rwnd_AckNum = rwnd_decode_data.split('$')[1]
                            rwnd_Ack = rwnd_decode_data.split('$')[2]
                            is_rwnd = rwnd_decode_data.split('$')[6]
                            if (int(is_rwnd)):  # rwnd waiting packet
                                # ACK last sent rwnd wait packet
                                if (int(rwnd_Ack) and int(rwnd_AckNum) == rwnd_seq):
                                    rwnd_val = int(
                                        rwnd_decode_data.split('$')[7])
                                    if (rwnd_val != 0):  # rwnd not zero, recover to send data
                                        self.sendWindowSize = rwnd_val
                                        break
                                    else:  # Still waiting and increase wait pkt seq num
                                        rwnd_seq += 1
                            else:  # Not rwnd waiting pkt
                                # if delayed previous data pkt ack, update window state
                                if (ack_index >= lastAck and ack_index < lastSend):
                                    window[window_index] = 1
                                    print(
                                        'SEND: Fragment-%d sends successfully!' % ack_index)

                    while lastSend < total_pkt and lastSend - lastAck < self.sendWindowSize:
                        seqNum = origin_seq + self.MSS * lastSend
                        print('SEND: Begin sending Fragment-%d(SeqNum:%d)...' %
                              (lastSend, seqNum))
                        header = packet_header(SeqNum=seqNum, Flag=Flag())
                        pkt = packet(packet_header=header,
                                     data=data_packets[lastSend])
                        self.sock.sendto(pkt.getStr().encode(), self.csAddr)
                        lastSend += 1
                if lastAck == total_pkt - 1:
                    print('SEND: Data sends successfully')
                    print('-'*15, ' END SEND ', '-'*15, '\n')
                    return True

        print('SEND: Something WRONG, try agin...')
        print('-'*15, ' END SEND ', '-'*15, '\n')
        return False

    def rdp_recv(self, size):
        '''
        Receive up to buffersize bytes from the socket.
        When no data is available, block until at least one byte is available
        or until the remote end is closed.
        When the remote end is closed and all data is read, return the empty string.
        '''
        if size > self.rcv_bufferSize:  # Less than buffersize
            raise ValueError
        if size == 0:  # Not retrieve data
            return ''
        # Retrieve data but buffer still filled
        if ((self.rcv_bufferSize - (len(self.rcv_buffer) - size)) <= 0):
            return self.rcv_buffer[:size]

        window = [[0, ''] * self.recvWindowSize]
        cnt = 0
        ack_cnt = 0
        flag = Flag(ACK=1)
        origin_seq = random.randint(1, 10)
        while True:
            try:
                rcv_data, rcv_addr = self.sock.recvfrom(1024)
            except:
                if cnt < 3:
                    print('RECV: Waiting packets from (%s:%s)...' % self.csAddr)
                    cnt += 1
                    continue
                else:
                    print('RECV: No data received from (%s:%s). Finish' %
                          (self.csAddr))
                    break

            if (rcv_addr == self.csAddr):  # From client/server pkt
                decode_data = rcv_data.decode()
                decode_seqNum = int(decode_data.split('$')[0])
                decode_wrw = int(decode_data.split('$')[6])
                if (decode_wrw):  # Wait rwnd pkt
                    print('RECV: Waiting rwnd pkt, send ack...')
                    rwnd_flag = Flag(ACK=1, WRW=1)
                    rwnd = self.rcv_bufferSize-len(self.rcv_buffer)
                    rwnd = 0 if (rwnd <= 0) else rwnd
                    header = packet_header(
                        SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=rwnd_flag, rwnd=rwnd)
                    pkt = packet(header, '')
                    self.sock.sendto(pkt.getStr().encode(), self.csAddr)
                    ack_cnt += 1
                else:  # Not wait rwnd pkt
                    back_ack = self.rcv_base - self.recvWindowSize * self.MSS
                    if (back_ack >= 0 and decode_seqNum < self.rcv_base and back_ack >= decode_seqNum):
                        # [rcv_base-N, rcv_bace) pkt, resend ACK in case sender repeat resending
                        print('RECV: Before window pkt, resend ack...')
                        rwnd = self.rcv_bufferSize-len(self.rcv_buffer)
                        header = packet_header(
                            SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=flag, rwnd=rwnd)
                        pkt = packet(header, '')
                        self.sock.sendto(pkt.getStr().encode(), self.csAddr)
                        ack_cnt += 1
                    elif (decode_seqNum > self.rcv_base and decode_seqNum <= self.rcv_base+(self.recvWindowSize-1)*self.MSS):
                        # (rcv_base, rcv_base+(N-1)*MSS] pkt, buffer pkt
                        print('RECV: Inside window pkt(SeqNum:%d), buffer data' %
                              decode_seqNum)
                        seq_index = int(
                            (decode_seqNum - self.rcv_base)/self.MSS)

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
                        rwnd = self.rcv_bufferSize-len(self.rcv_buffer)
                        rwnd = 0 if (rwnd <= 0) else rwnd
                        header = packet_header(
                            SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=flag, rwnd=rwnd)
                        pkt = packet(header, '')
                        self.sock.sendto(pkt.getStr().encode(), self.csAddr)
                        ack_cnt += 1

                    if decode_seqNum == self.rcv_base:
                        print(
                            'RECV: Window start pkt(SeqNum:%d), buffer continual data' % decode_seqNum)
                        rwnd = self.rcv_bufferSize-len(self.rcv_buffer)
                        header = packet_header(
                            SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=flag, rwnd=rwnd)
                        pkt = packet(header, '')
                        self.sock.sendto(pkt.getStr().encode(), self.csAddr)
                        ack_cnt += 1

                        # Set data for rcv_base
                        seq_index = int(
                            (decode_seqNum - self.rcv_base)/self.MSS)
                        window[seq_index][0] = 1
                        temp = ''
                        for index, val in enumerate(decode_data.split('$')[utils.data_index:]):
                            if (index == 0):
                                temp += val
                            else:
                                temp = temp + '$' + val
                        window[seq_index][1] = temp

                        # Add continual data to buffer
                        for w in window:
                            if int(w[0]):
                                self.rcv_buffer += w[1]
                                self.rcv_base += self.MSS
                                w[0] = 0
                                w[1] = ''
                            else:
                                break
                        # print('RECV: Buffer: ', self.rcv_buffer)

                        # Return at most size data
                        data = self.rcv_buffer[:size-1]
                        self.rcv_buffer = self.rcv_buffer[size:]
                        return data
        data = self.rcv_buffer[:size-1]
        self.rcv_buffer = self.rcv_buffer[size:]
        return data

    def resetRecv(self):
        '''
        Reset the recv state after a transmission.
        '''
        self.rcv_base = 0

    def makeConnection(self, addr, port):
        '''
        Make connection with server(addr:port)
        '''
        print('\n')
        print('-'*15, ' BEGIN HANDSHAKE ', '-'*15)

        addr = '127.0.0.1' if (addr == 'localhost') else addr
        # Send SYN Packet
        print('CONNECT: Start handshake with server(%s:%s)' % (addr, port))
        flag = Flag(SYN=1)
        seq = random.randint(1, 10)
        header = packet_header(SeqNum=seq, Flag=flag)
        pkt = packet(header, '')
        print('CONNECT: Send SYN to server(%s:%s): %s' %
              (addr, port, pkt.getStr()))
        self.sock.sendto(pkt.getStr().encode(), (addr, port))

        cnt = 0
        while True:
            # Wait ACK Packet
            try:
                rcv_data, rcv_addr = self.sock.recvfrom(1024)
            except:
                # No confirm SYN packet, resend SYN
                if cnt < 5:
                    print('CONNECT: Timeout for receiving ACK from server(%s:%s)...\nResending...' % (
                        addr, port))
                    pkt = packet(header, '')
                    self.sock.sendto(pkt.getStr().encode(), (addr, port))
                    cnt += 1
                    continue
                else:
                    print('CONNECT: ERROR:\nHandshake with server(%s:%s) failed with server ERROR!' % (
                        addr, port))
                    print('-'*15, ' END HANDSHAKE ', '-'*15)
                    return False

            data = rcv_data.decode()
            print('CONNECT: Packet from (%s): %s' % (rcv_addr, data))
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
            print('CONNECT: ACK confirmed, send ACK to server(%s): %s' %
                  (rcv_addr, pkt.getStr()))
            self.sock.sendto(pkt.getStr().encode(), (addr, port))
            # Handshake finish
            self.csAddr = (addr, int(new_port))
            print('CONNECT: Handshake with server(%s:%s) successfully!' %
                  self.csAddr)
            print('-'*15, ' END HANDSHAKE ', '-'*15)
            return True

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
                    print('LISTEN: SYN from client(%s): %s' % (rcv_addr, data))
                    self.new_port[rcv_addr] = utils.getPort()
                    header = packet_header(
                        SeqNum=self.seq[rcv_addr], ACKNum=decode_seqNum, Flag=flag)
                    pkt = packet(header, self.new_port[rcv_addr])
                    print('LISTEN: ACK to client(%s): %s' %
                          (rcv_addr, pkt.getStr()))
                    self.sock.sendto(pkt.getStr().encode(), rcv_addr)
                # ACK receive, check if sent SYN
                decode_ackNum = data.split('$')[1]
                print('LISTEN: ACK from client(%s): %s' % (rcv_addr, data))

                if (int(decode_ack) and rcv_addr in self.seq and
                        int(decode_ackNum) == self.seq[rcv_addr]):
                    self.cnt += 1
                    print('LISTEN: Handshake finish with client(%s): %s' %
                          (rcv_addr, data))
                    self.clientSock.append(
                        [rcv_addr, RDP(port=(self.new_port[rcv_addr]))])
            else:
                # break
                print(
                    'LISTEN: Serving MAX Client. New Client(%s:%s) request abandoned', rcv_addr)

    def accept(self):
        '''
        Retrieve a client-connected RDP;
        If no connection, none is returned
        '''
        if (len(self.clientSock) > 0):
            temp = self.clientSock.pop()
            del self.seq[temp[0]]
            temp[1].csAddr = temp[0]  # set client addr
            return temp[1]
        return None

    def release(self):
        '''
        Cancel a client-connected RDP;
        Return the sock running address(addr, port)
        '''
        pair = self.sock.getsockname()
        self.cnt -= 1
        self.sock.close()
        return pair

    def releasePort(self, port):
        '''
        Release the port
        '''
        for item in self.new_port.items():
            if item[1] == port:
                del self.new_port[item[0]]
                break

    def getLocalAddr(self):
        '''
        Return the RDP running local address in a pair (addr, port)
        '''
        return self.sock.getsockname()
