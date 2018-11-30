# Design

LFTP uses RDP Protocol, based on UDP, to finish **sending/getting large file between either server or client side**.
RDP implements the **reliability, flow control and congestion control** as TCP.

## Server side

1. Implement the data sending(client getting file) by calling the function `RDP.send(data, addr)`
2. Implement the data downloading(client uploading file) by calling the function `RDP.get(file, addr)`
3. Support multiple client by multiple thread function
   
## Client side

1. Implement the data sending(uploading file) by calling the function `RDP.send(data, addr)`
2. Implement the data receiving(downloading file) by calling the function `RDP.get(file, addr)`

## RDP Protocol

1. Implement the packet sending(data & handshake) by `rdp_send(packet)`
    - Packet fragmentation(MSS)
    - Send packet in pipe line
    - Flow control
    - Congestion control
2. Implement the packet receiving(data & ACK & handshake)
    - Receive Buffer
3. `send(data, addr)` for application layer
4. `get(file, addr)` for application layer

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
      <td align="center">Flag Field<br>(ACK, RST, SYN, FIN)</td>
    </tr>
    <tr>
      <td align="center">Receive Window</td>
    </tr>
    <tr>
      <td align="center" colspan=2>CheckSum</td>
    </tr>
    <tr>
      <td align="center" colspan=2>Data</td>
    </tr>
  </tbody>
</table>
