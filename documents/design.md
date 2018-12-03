# Design

## Description

LFTP using RDP Protocol, a UDP based protocol, helps **sending/getting large file between either server or client side**.
RDP implements the **reliability, flow control and congestion control** as TCP.

## Transport Layer: RDP Protocol

> Author: Weiyuan Xu

### Example of Using RDP

- Server
  
  ```python
  from rdp import *
  server = RDP(addr=serverRunningAddress, port=serverRunningPORT)
  # Set the max serving clients
  # ATTENTION: Must run in a thread
  server.listen(num)

  # Retrieve a connected socket
  # ATTENTION: Serve the client in a thread
  while (connectSock = server.accept()) != None:
    data = connectSock.rdp_recv(bufferSize)
    # Analysis data command
    if getFileCommand:
      if connectSock.rdp_send(okCommand):
        connectSock.rdp_send(file)
    else if sendFileCommand:
      if connectSock.rdp_send(okCommand):
        connectSock.rdp_recv(bufferSize)
    else if quitCommand:
      addr = connectSock.release()
      # inform the listen server to release the port in addr
      server.releasePort(addr[1])
  ```

- Client

  ```python
  from rdp import *
  client = RDP(Client=True)

  client.makeConnection(addr=ServerAddress, port=serverPort)
  if client.rdp_send(sendFileCommand):
    data = rdp_recv(bufferSize)
    if data == ok:
      client.rdp_send(file)
  if client.rdp_send(GetFileCommand):
    data = client.rdp_recv(bufferSize)  # Get file
    # Once finish get the whole file, reset the recv state
    client.resetRecv()
    if data == ok:
      file = client.rdp_recv(bufferSize):  # Get file
      
  
  client.rdp_send(data:quitCommand) # End connection with server

  # Finally release socket
  client.release()
  ```

### RDP Design 

RDP Protocol provides the **reliability, flow control, congestion control** like TCP based on UDP. Let's start introducing how RDP protocol is designed to retrieve the goal.

- **Design From Request**
  - **Fundament**
    According to the Application layer requests, *send data and receive data* function are fundamental and application needn't know the implementation. Thus, we first design two functions: **`rdp_send(data)`** to send data and **`rdp_recv(size)`** to get data.
    Furthermore, these two function should act like TCP, which means application just invokes functions and **knows** where it get/send data. So we need to make connection between server and client before invoking these functions with *handshake behavior*. **`makeConnection(targetAddress)`** is needed.
  - **Reliable**
    RDP is based on UDP, which is not reliable. We have to add something to make sure the reliability. Consider the rdt FSM shown in Chapter 3 in book(*Computer Networking, a top-down approach, six edition, James F.Kurose*), we get the idea. Set the data field in UDP packet as below:
    <table>
      <thead>
        <tr>
          <th align="center" colspan=2>
          UDP packet data field
          </th>
        </tr>
      </thead>
      
      <tbody>
        <tr>
          <td align="center" colspan=2>Sequence Number</td>
        </tr>
        <tr>
          <td align="center" colspan=2>Acknowledgement Number</td>
        </tr>
        <tr>
          <td align="center">Flag Field<br>(ACK, SYN, RST, FIN)</td>
        </tr>
        <tr>
          <td align="center" colspan=2>Data</td>
        </tr>
      </tbody>
    </table>
    The usage of seqNum(Sequence Number) and ACKNum(Acknowledgement Number) are used to make sure pkt(packet) is truly sent to destination. Once we send a pkt labeled with seqNum, receiver must send a ACK pkt to sender with ACKNum equals the seqNum obtained in pkt received.
    The flag field is used to distinguish the kind of pkt(e.g. ACK means ACK pkt, SYN means handshake request pkt). Data is the real data we want to send.
  - **Multiple Client**
    Since server must support multiple client, the server application(host) must handle the clients at the same time. So **multiple thread** is needed. We provide each connected client a *server program* running in different *port*. So we design **`listen(num)`** function to *listen* the connection requests from clients and maximum number of client for server to serve is `num`. The listen function provides the *listening* and helps make connection between server and client. Hence, sockets are created when connection successfully made in `listen`, we must export the serving socket for server application. **`accept()`** retrieve a serving socket and server application must run the socket in a thread and handle it.

  - **Summary**
    **`rdp_send(data)`**,**`rdp_recv(size)`**,**`makeConnection(targetAddress)`**,**`listen(num)`** and **`accept()`** are the most important function designed in RDP. Following, we will introduce the implementation and the detail design of them.
- **Inside Function**
  - **`makeConnection(targetAddress)`** and **`listen(num)`**
    `makeConnection` helps make connection with client and server. We only invoke it in client side. First, it send SYN pkt and waits server to send ACK pkt. After receiving the ACK from server, client send ACK to client and the *handshake* or connection is established.
    Though, it helps us make connection, the socket keeps the targetAddress is a problem. Because the targetAddress is linked to the server listening application. We need to bind the client with the correct port of serving application(*Client just need to know the server running at the 8080 port and makeConnection with it, but server using different port to handle multiple clients. So it is important for client socket to know which port in server is serving it and **communicate** with serving application through that port*). We deal with the problem with the idea of server sending the port to client in ACK pkt and waiting for the ACK to truly create a socket to server the client. Why creation happens when server receive from client? Because the *SYN flood* attack. If we create a socket while receiving a SYN pkt, server will soon run out of resource for serving the true client when somebody just send SYN to sever but not response ACK to server's ACK pkt.
  - **`rdp_send(data)`**
    Because we must implement the flow control and congestion control. We need to add some variables to help. For controlling the sending rate, we use `sendWindowSize` to help. It acts like the size of the receive window which tells the most size of the send pkt.
    
    For flow control, we use `buffer` and `bufferSize` to help. In our design, once the rdp_recv(bufferSize) function is invoked, at most bufferSize data is returned. So the lastByteRead is always zero and the len(rcv_buffer) is the lastByteRecv. Then the rwnd = BufferSize - (lastByteRecv - lastByteRead) = BufferSize - len(rcv_buffer). The receiver include the receive window size inside the ACK pkt, so we add **`rwnd`** field into the UDP data field. Also, when the rwnd is zero, sender must wait. We design a special flag **`WRW`**(wait receive window) to label a pkt, which is used to loop asking the receiver the rwnd when rwnd is zero. This prevents sender not knowing the receiver have buffer to get data after last ACK pkt with rwnd equals zero. And sender does not send any data to receiver because it is told receiver have no space for data and receiver will never send a new rwnd to sender.
    
    For congestion control, we need to trace a variable **`cwnd`** in sender. Also, `ssthresh` and `dupACK` helps turning the state of the sender to control the sending rate in case of the congestion in network. We set slow start state, congestion avoidance state and fast recovery state as integer number to distinguish. We handle different cwnd behavior based on the state code.
    And we adjust the sending window size with the formula: size = min{cwnd, rwnd}. The size helps determine the pkt numbers to send in case overflow the buffer in receiver and congestion in network.
  - **`rdp_recv(size)`**
    It receive data from sender and return data in buffer to application. To match the flow control, we must determine if receive data from sender. So we must see the data size application wants which is the parameter `size` make space for further data. And once we send ACK pkt, the rwnd is calculated and sent, too. More interesting thing is that, we design a *buffer for buffer*. When rwnd is not zero, sender sends data. But the data sender sends makes buffer overflow. In this case, we still buffer this data, because it is a waste to abandon the pkt if we just set a *buffer for buffer*. We hide the real rwnd because it is less than zero in this case, and just send zero as rwnd to sender. And after, application invoke `rdp_recv(size)`, we will determine if the size of data make space to receive more data from sender. If yes, we get data from remote. Otherwise, we just return application the data in buffer and not get data from remote.
- **Packet Structure**
  This is the final pkt structure after taking the consideration above.
  <table>
    <thead>
      <tr>
        <th align="center" colspan=2>
        UDP packet data field
        </th>
      </tr>
    </thead>
    
    <tbody>
      <tr>
        <td align="center" colspan=2>Sequence Number</td>
      </tr>
      <tr>
        <td align="center" colspan=2>Acknowledgement Number</td>
      </tr>
      <tr>
        <td align="center">Flag Field<br>(ACK, SYN, RST, FIN, WRW)</td>
      </tr>
      <tr>
        <td align="center" colspan=2>rwnd</td>
      </tr>
      <tr>
        <td align="center" colspan=2>Data</td>
      </tr>
    </tbody>
  </table>
- **Summary**
  More details could be found in [code](https://github.com/xwy27/LFTP/tree/master/code) with detail comments and in book, *Computer Networking, a top-down approach, six edition, James F.Kurose*. Most of the idea are inspired from the book for it gives a detail picture. Moreover, thanks to my group member, Yongqi Xiong([SiskonEmilia](https://github.com/SiskonEmilia)), who listens to my complaint and forgives my idiot fault.

## Application Layer: LFTP

> Author: Yongqi Xiong

### Server side

1. Implement the data sending(client getting file) by calling the function `RDP.rdp_send(data)`
2. Implement the data downloading(client uploading file) by calling the function `RDP.rdp_get(size)`
3. Support multiple client by multiple thread function
   
### Client side

1. Implement the data sending(uploading file) by calling the function `RDP.rdp_send(data)`
2. Implement the data receiving(downloading file) by calling the function `RDP.rdp_get(size)`
