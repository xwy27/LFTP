# -*- coding:utf-8 -*-
import socket
import random
import enum
import sys
import traceback
import time

import utils
from rdp_header import *

exit = False


class RDP():
    '''
    Create a socket running RDP at addr:port
    '''

    def __init__(self, addr='localhost', port=10000, client=False):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if not client:
            self.sock.bind((addr, port))  # Bind local addr for sock
            print('Server RDP running on %s:%s' % self.sock.getsockname())
        else:
            print('Client RDP running')
        self.csAddr = ('', 0)  # Bind client or server address
        self.sock.settimeout(1)  # set timeout seconds

        self.MSS = 60000  # Max Sending Size
        self.sendWindowSize = 128  # max size of the sending window
        self.recvWindowSize = 128  # max size of the receiving window
        self.originSeq = 0  # for sender, the origin sequence number
        self.lastAck = 0  # for sender to check the last ack packet in pipline
        self.lastSend = 0  # for sender to check the last send packet in pipline

        self.rcv_base = 0  # for receiver to check the hoping receive pkt

        # ATTENTION:
        # Once invoked the rdp_recv(bufferSize) function, at most bufferSize data is returned
        # So the lastByteRead is always zero and the len(rcv_buffer) is the lastByteRecv
        # The rwnd = BufferSize - (lastByteRecv - lastByteRead) = BufferSize - len(rcv_buffer)
        self.rcv_buffer = ''  # buffer for rcv_data
        self.rcv_bufferSize = 4096000  # buffer size

        self.congessState = 0 # Congession control state, 0: slowStart, 1:congessionAvoid, 2:fastRecovery
        self.cwnd = self.MSS # Congession Window
        self.dupACK = 0 # count for duplicate ACK
        self.ssthresh = 64000 # 

        self.clientSock = []  # Activate sockets for server to serve client
        self.seq = {} # Sequence Numbers to SYN clients
        self.cnt = 0 # Count for connected clients 
        self.new_port = {} # Ports distributed for SYN clients

    def rdp_send(self, data):
        '''
        Send a data string to the socket.
        Return true if sent successfully, otherwise false;
        this may be less than len(data) if the network is busy.
        '''
        print('\n')
        print('-'*15, ' BEGIN SEND ', '-'*15)
        print(self.csAddr)

        # Split the data
        fragment_size = 0
        if len(data) % self.MSS != 0:
            fragment_size = len(data)/self.MSS + 1
        else:
            fragment_size = len(data)/self.MSS

        data_packets = [data[x*self.MSS:x*self.MSS+self.MSS]
                        for x in range(int(fragment_size))]
        lastAck = self.lastAck  # for sender to check the last ack packet in pipline
        lastSend = self.lastSend  # for sender to check the last send packet in pipline
        origin_seq = self.originSeq  # origin sequence number
        total_pkt = len(data_packets)  # Total num of data packets to send
        # Sender window, 0 for not ack, 1 for ack
        window = []
        for x in range(self.sendWindowSize):
            window.append(0)
        while (lastSend - origin_seq) < total_pkt and lastSend - lastAck < self.sendWindowSize:
            seqNum = lastSend
            print('SEND: Begin sending Fragment-%d(SeqNum:%d)...' %
                  (lastSend, seqNum))
            header = packet_header(SeqNum=seqNum, Flag=Flag())
            pkt = packet(packet_header=header,
                         data=data_packets[lastSend-lastAck])
            self.sock.sendto(pkt.getStr().encode(), self.csAddr)
            lastSend += 1

        timeout_cnt = 0  # counter for timeout
        while True:
            # time.sleep(0.05)
            try:
                rcv_data, rcv_addr = self.sock.recvfrom(self.MSS + 256)
            except Exception as e:
                print(traceback.format_exc())
                print('-'*15)
                print(e)
                print('-'*15)
                # No ACK packet, resend fragment
                if timeout_cnt < 5:
                    print('SEND: Timeout for receiving ACK from(%s:%s)...' %
                          self.csAddr)
                    for index, win in enumerate(window):
                        if not int(win):
                            pkt_index = lastAck - origin_seq + index
                            fragment_index = lastAck + index
                            if pkt_index < total_pkt:
                                print('SEND: Resending fragment-%d ...' %
                                      fragment_index)
                                seqNum = fragment_index
                                header = packet_header(
                                    SeqNum=seqNum, Flag=Flag())
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
                ack_index = int(decode_ackNum)
                window_index = int(decode_ackNum) - lastAck
                print('SEND: ACK pkt(ACKNum:%d, windowIndex:%d, lastACK:%d, lastSend:%d)' % (
                    int(decode_ackNum), window_index, lastAck, lastSend))
                if (ack_index > lastAck and ack_index < lastSend):
                    decode_rwnd = decode_data.split('$')[7]
                    # Update sending window size
                    temp = int(int(decode_rwnd) / self.MSS)
                    self.sendWindowSize = 0 if temp < 1 else temp
                    window = self.resetWindow(window, self.sendWindowSize)
                    window[window_index] = 1
                    print('WindowIndex: ', window_index)
                    print(
                        'SEND: Fragment-%d sends successfully!(Waiting to move window...)' % ack_index)
                elif (ack_index == lastAck):
                    print(
                        'SEND: Fragment-%d sends successfully!(Move Window)' % ack_index)
                    decode_rwnd = decode_data.split('$')[7]
                    # Update sending window size
                    temp = int(int(decode_rwnd) / self.MSS)
                    self.sendWindowSize = 0 if temp < 1 else temp
                    window[window_index] = 1
                    # print('first: ', window[0], ' second: ', window[1])
                    for index, win in enumerate(window):
                        if int(win):
                            lastAck += 1
                            window[index] = 0
                        else:
                            break
                    window = self.resetWindow(window, self.sendWindowSize)
                    # print('first: ', window[0], ' second: ', window[1])

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
                                        temp = int(rwnd_val / self.MSS)
                                        self.sendWindowSize = 0 if temp < 1 else temp
                                        window = self.resetWindow(
                                            window, self.sendWindowSize)
                                        break
                                    else:  # Still waiting and increase wait pkt seq num
                                        rwnd_seq += 1
                            else:  # Not rwnd waiting pkt
                                # if delayed previous data pkt ack, update window state
                                if (ack_index >= lastAck and ack_index < lastSend):
                                    win_index = int(
                                        rwnd_AckNum) - origin_seq - lastAck
                                    window[win_index] = 1
                                    print(
                                        'SEND: Fragment-%d sends successfully!' % ack_index)

                    while lastSend-origin_seq < total_pkt and lastSend - lastAck < self.sendWindowSize:
                        seqNum = lastSend
                        print('SEND: Begin sending Fragment-%d(SeqNum:%d)...' %
                              (lastSend, seqNum))
                        header = packet_header(SeqNum=seqNum, Flag=Flag())
                        pkt = packet(packet_header=header,
                                     data=data_packets[lastSend-origin_seq])
                        self.sock.sendto(pkt.getStr().encode(), self.csAddr)
                        lastSend += 1
                print(lastSend, lastAck, origin_seq)
                if lastAck-origin_seq-1 == total_pkt-1:
                    self.originSeq = lastAck
                    self.lastAck = lastAck
                    self.lastSend = lastSend
                    print('SEND: Data sends successfully')
                    print('-'*15, ' END SEND ', '-'*15, '\n')
                    return True
        self.originSeq = lastAck
        self.lastAck = lastAck
        self.lastSend = lastSend
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

        # window = [[0, ''] * self.recvWindowSize]
        window = []
        for x in range(self.recvWindowSize):
            window.append([0, ''])
        cnt = 0
        ack_cnt = 0
        flag = Flag(ACK=1)
        origin_seq = random.randint(1, 10)
        print(self.rcv_base)
        while True:
            try:
                rcv_data, rcv_addr = self.sock.recvfrom(self.MSS + 256)
            except:
                if cnt < 5:
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
                    back_ack = self.rcv_base - self.recvWindowSize
                    print('RCV_Packet: ', decode_seqNum)
                    print('back: ', back_ack)
                    if (back_ack >= 0 and decode_seqNum < self.rcv_base and back_ack >= decode_seqNum):
                        # [rcv_base-N, rcv_bace) pkt, resend ACK in case sender repeat resending
                        print('RECV: Before window pkt, resend ack...')
                        rwnd = self.rcv_bufferSize-len(self.rcv_buffer)
                        header = packet_header(
                            SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=flag, rwnd=rwnd)
                        pkt = packet(header, '')
                        self.sock.sendto(pkt.getStr().encode(), self.csAddr)
                        ack_cnt += 1
                    elif (decode_seqNum > self.rcv_base and decode_seqNum <= self.rcv_base+self.recvWindowSize-1):
                        # (rcv_base, rcv_base+(N-1)] pkt, buffer pkt
                        print('RECV: Inside window pkt(SeqNum:%d), buffer data' %
                              decode_seqNum)
                        seq_index = int(
                            decode_seqNum - self.rcv_base)

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
                    elif decode_seqNum == self.rcv_base:
                        print(
                            'RECV: Window start pkt(SeqNum:%d), buffer continual data' % decode_seqNum)
                        rwnd = self.rcv_bufferSize-len(self.rcv_buffer)
                        header = packet_header(
                            SeqNum=origin_seq+ack_cnt*1, ACKNum=decode_seqNum, Flag=flag, rwnd=rwnd)
                        pkt = packet(header, '')
                        self.sock.sendto(pkt.getStr().encode(), self.csAddr)
                        ack_cnt += 1
                        print('ACK pkt: ', decode_seqNum)

                        # Set data for rcv_base
                        seq_index = int(
                            decode_seqNum - self.rcv_base)
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
                                self.rcv_base += 1
                                w[0] = 0
                                w[1] = ''
                            else:
                                break

                        # Return at most size data
                        data = self.rcv_buffer[:size-1]
                        self.rcv_buffer = self.rcv_buffer[size:]
                        return data
                    else:
                        print("WOW, here we drop a packet!!!!", decode_seqNum)
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
        global exit
        self.seq = {}
        self.cnt = 0
        # self.clientPort = {}
        self.new_port = {}
        while True:
            time.sleep(0.2)
            if exit:
                return
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
                        [rcv_addr, RDP(addr=self.getLocalAddr()[0], port=(self.new_port[rcv_addr]))])
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
        self.sock.close()
        return pair

    def releasePort(self, port):
        '''
        Release the port
        '''
        for item in self.new_port.items():
            if item[1] == port:
                self.cnt -= 1
                del self.new_port[item[0]]
                break

    def getLocalAddr(self):
        '''
        Return the RDP running local address in a pair (addr, port)
        '''
        return self.sock.getsockname()

    def resetWindow(self, window, newSize):
        newWindow = []
        for x in range(newSize):
            if x < len(window):
                newWindow.append(window[x])
            else:
                newWindow.append(0)
        return newWindow
