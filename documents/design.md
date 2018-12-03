# Design

LFTP uses RDP Protocol, based on UDP, to finish **sending/getting large file between either server or client side**.
RDP implements the **reliability, flow control and congestion control** as TCP.

## Usage

Before you use this program, on the server-side, you should make a folder named `data` under `code/` first to store the files to exchange with clients:

```shell
cd code
mkdir data
```

Then, you could run command below to run the program on the server:

```shell
# use python 3.x
python ./server.py [hostname port]
# default hostname: localhost
# default port: 8080
```

After that, you could run the command below to connect and exchange files with the server:

```shell
# use python 3.x
python ./client.py lget/lsend hostname[:port] filename
# default port: 8080
```

Hope you enjoy your time with it.

## Transport Layer: RDP Protocol

1. Implement the packet sending(data & handshake) by `rdp_send(data)`
    - Packet fragmentation(MSS)
    - Send packet in pipe line
    - Flow control
    - Congestion control
2. Implement the packet receiving(data & ACK & handshake) by `rdp_recv(size)`
    - Receive Buffer

### Packet

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

### Example of Using RDP

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

## Application Layer: LFTP

### Server side

#### Target


1. Support multiple client by multiple thread function
1. Implement the data sending(client getting file) by calling the function `RDP.rdp_send(data)`
1. Implement the data downloading(client uploading file) by calling the function `RDP.rdp_get(size)`

#### Multiple User

In order to implement multiple user support, we introduce multi-thread architecture to this project. With multi-thread technique, we handle each user's request with a single thread, which could run concurrently with other threads. Thus we can handle plushy users' request 'at the same time': 

```python
listenThread = threading.Thread(target=listen, args=(hostname, port), name="Listen Thread")
listenThread.start()
console()
```

Further more, multi-thread architecture also makes it possible for us to response to the requests of users to make connection and handle the requests of users who has made connection concurrently:

```python
server = RDP.RDP(addr=hostname, port=int(port))
listenThread = threading.Thread(target=server.listen, args=(10,), name="basic listening")
listenThread.start()
while True:
  time.sleep(0.1)
  # If the user is trying to exit
  if exit:
    # Stop the listen thread
    RDP.exit = True
    if threading.active_count() == 2:
      break
    else:
      time.sleep(0.5)
      continue
  
  serverLock.acquire()
  clientSocket = server.accept()
```

What worth being paying attention to is that, every dead loop in a thread may affects the speed of other threads to execute code. A good practice is to introduce `time.sleep` into each thread to balance the computing resources given to each thread.

In the very following of the execution of the server-side program, we will deploy a listener at the given hostname and port number, then internally accept the requests of users to make connection, and we will allocate a new port for the user to access the server (and exchange data with it on). After that, we will construct a socket to handle this connection, then create a new thread to handle these commands sent from users.

A critical issue lead by multiple users support is the **Writer-Reader Problem**, which means concurrent writing and reading on the same file may results in an unexpected error. To get rid of this trouble, we introduce `Thread Lock` to our program. Any writer needs to acquire a writer lock (there's only one such lock for each file) before they begin to write while making sure no reader is reading the file, and every reader needs to make sure no writer is writing before they begin to read. In practice, taking writing method as an example, we implement it as below:

```python
print("Receiving %s: Acquiring Dictionary Lock..." % filename)
dictLock.acquire()
print("Receiving %s: Dictionary Lock Acquired" % filename)
# Try to get the writer lock
if filename not in wLockDict:
  print("Receiving %s: Initializing File Lock..." % filename)
  # If no lock is initialized, create one
  wLockDict[filename] = threading.Lock()
  # Get the writer lock
  print("Receiving %s: Acquiring file writing lock..." % filename)
  wLockDict[filename].acquire()
  print("Receiving %s: File writing lock Acquired." % filename)    
  rLockDict[filename] = threading.Lock()
  rCountDict[filename] = 0
  dictLock.release()
  print("Receiving %s: Dictionary Lock Released." % filename)
else:
  dictLock.release()
  print("Receiving %s: Dictionary Lock Released." % filename)
  # Get the writer lock
  print("Receiving %s: Acquiring file writing lock..." % filename)
  wLockDict[filename].acquire()
  print("Receiving %s: File writing lock Acquired." % filename)    
  while rCountDict[filename] != 0:
    time.sleep(0.5)

###################
# Write file here #
###################

# End of writing
print("Receiving %s: File Lock Released." % filename)
wLockDict[filename].release()
```

#### Sending Data

When the user sends a command like `lget filename`, we will try to find a file of filename and send it to the user:

First, we will check the existence of target file with `os.path.exists()`, if no such file exists, an error message will be sent to the client.

```python
if not os.path.exists("data/" + filename):
  socket.rdp_send("NO")
  print("Sending file %s: No such file." % filename)
  return
```

Then, we'll get the length of the file with `os.stat().st_size`, pack it with an OK message, and send them to the client.

```python
if not socket.rdp_send("OK\n" + str(length)):
  print("Sending file %s: No such file." % filename)
  return
```

After we get the confirm of client of receiving the message above, we'll start to read some data from the file and send them to the client internally before the length of data sent successfully equals to the total length of the whole file. 

```python
with open("data/" + filename, "rb") as f:
  start_time = time.time()
  while sentLength != length:
    line = f.read(20480)
    if not socket.rdp_send(base64.b64encode(line).decode("ASCII")):
      print("Error while sending file %s." % filename)
      return
    sentLength += len(line)
    print("Sending file %s: %d%% done." % (filename, sentLength / length * 100))
    print("Speed: %d KB/s" % (sentLength / (time.time() - start_time + 0.01) / 1000))
  print("Sending done.")
```

To better pack our RDP packet, we need to convert every byte in the binary file to base64 format, and use ASCII to format it into a literal string.

#### Getting Data
   
Getting data from clients is like an inverse progress of sending data to them. Thus after we get command like `lsend filename length` from clients, we will send `OK` message to confirm that we're ready to receive the file:

```python
if not socket.rdp_send("OK"):
  print("Receiving %s: Connection Error: Fail when asking client to send file." % filename)
  wLockDict[filename].release()
  return 
```

After we receive the ACK packet from clients, we begin to receive those data that clients sends till the length of data we accepted equals to the length that the client claims the file to have:

```python
with open("data/" + filename, "wb") as f:
  start_time = time.time()
  while True:
    # User want to exit
    if exit:
      print("Receiving %s: Server is exiting..." % filename)
      break
    # Finish
    if acLength == length:
      print("Receiving %s: Done" % filename)
      break
    # Receive some data
    metadata = socket.rdp_recv(30720)
    while len(metadata) % 4 != 0:
      temp = socket.rdp_recv(30720)
      if len(temp) == 0 :
        metadata = ""
        break
      metadata += temp
      
    data = base64.b64decode(metadata.encode("ASCII"))
    if len(data) == 0:
      print("Receiving %s: Connection Error: Timeout when receiving data." % filename)
      break
    acLength += len(data)
    print("Receiving %s: %d%% data received..." % (filename, acLength / length * 100))
    # Write to file
    f.write(data)
    print("Speed: %d KB/s" % (acLength / (time.time() - start_time + 0.01) / 1000))
```

There's an issue you need to pay sight on: base64 code must be a multiplex of 4 (actually, it encode every 3 bytes into 4 ASCII code), which means the existence of invalid length of data. Thus we need to judge if the data buffered is valid, and only decode the valid ones.

### Client side

1. Implement the data sending(uploading file) by calling the function `RDP.rdp_send(data)`
2. Implement the data receiving(downloading file) by calling the function `RDP.rdp_get(size)`

#### Make Connection

#### Sending Data

Client side program needs to corporate with the server side one to make the whole system work as expected. Thus before we begin to send data, we need to send our command

#### Getting Data
