# Design

LFTP uses RDP Protocol, based on UDP, to finish **sending/getting large file between either server or client side**.
RDP implements the **reliability, flow control and congestion control** as TCP.

## Server side

1. Implement the data sending(client getting file) by calling the function `RDP.rdp_send(data)`
2. Implement the data downloading(client uploading file) by calling the function `RDP.rdp_get(size)`
3. Support multiple client by multiple thread function
   
## Client side

1. Implement the data sending(uploading file) by calling the function `RDP.rdp_send(data)`
2. Implement the data receiving(downloading file) by calling the function `RDP.rdp_get(size)`

## RDP Protocol

1. Implement the packet sending(data & handshake) by `rdp_send(data)`
    - Packet fragmentation(MSS)
    - Send packet in pipe line
    - Flow control
    - Congestion control
2. Implement the packet receiving(data & ACK & handshake) by `rdp_recv(size)`
    - Receive Buffer

## Packet

Three kinds of packets which are determined by Flag field:
1. ACK packet
2. Data packet
3. Handshake packet

Designed packet structure:

<table>
  <thead>
    <tr>
      <th colspan=2>
      Packet Structure
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
      <td align="center">Receive Window</td>
    </tr>
    <tr>
      <td align="center" colspan=2>Data</td>
    </tr>
  </tbody>
</table>

## Example of Using RDP

- Server
  
  ```python
  from rdp import *
  server = RDP(addr=serverRunningAddress, port=serverRunningPORT)
  server.listen(num) # Dead loop

  connectSock = server.accept()
  while True:
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
