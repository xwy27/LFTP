# -*- coding:utf-8 -*-
import socket
import random

delimeter = '$'
data_index = 7


def getPort():
    '''
    Find an avaliable port num from 60000 to 10000 in localhost
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        port = random.randint(30000, 60000)
        try:
            sock.bind(('127.0.0.1', port))
        except:
            sock.close()
            # print(e)
            continue
        sock.close()
        return port
