import os
import sys
import time
import socket
import random
import optparse
from Serialization import *
from Global import *

class Server:
    def __init__(self,invocationSemantics1= 'AT_LEAST_ONCE',simulateLoss1 = False):
        self.UDP_ip = "localhost"                       # server ip
        self.UDP_port = 61032                           # port
        self.time = time.time()
        self.cache = []                                 # cache for requests from clients, used in 'at-most-once'
        self.cacheLimit = 10                            # cache size
        self.monitorList = []                           # monitoring list format: [address, filePathname]
        self.invocationSemantics = invocationSemantics1 # 2 invocation semantics: at least once, at most once
        self.simulateLoss = simulateLoss1               # switch of message loss simulation, default loss ratio = 50%
        self.dictPath = './file/'                       # all files created through this system will be stored under this directory
        self.dict = 'file'
        # create file dictionary
        if not os.path.exists(self.dict):
            os.mkdir(self.dict)

    # Create a socket and bind it to port
    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET,  # Internet
                                      socket.SOCK_DGRAM)  # UDP
        except socket.error as e:
            print('Failed to create socket:\n{}'.format(e))
            sys.exit()

        serverAddress = (self.UDP_ip, self.UDP_port)
        print('Starting server on {} Port {}...'.format(
            self.UDP_ip, self.UDP_port))

        print('Invocation semantics used: {}'.format(self.invocationSemantics))

        try:
            self.sock.bind(serverAddress)
        except socket.error as e:
            print('Socket bind failed:\n{}'.format(e))
            sys.exit()

        self.wait_for_req()   # Preparation done, start serving for clients

    def wait_for_req(self):
        while True:
            print('Server is waiting for request from client...')
            msg, address = self.sock.recvfrom(SOCK_MAX)
            # print(msg)
            print('Received request message from {}:\n{!r}'.format(address, msg))
            self.reply(msg, address)

    # Reply requests according to invocation semantics
    def reply(self, req, address):
        if req is None:
            raise ValueError("Received an empty Request!")
        if self.invocationSemantics == 'AT_LEAST_ONCE':
            self.replyAtLeastOnce(req, address)
        elif self.invocationSemantics == 'AT_MOST_ONCE':
            self.replyAtMostOnce(req, address)
        return

    def close_socket(self):
        print('Closing socket...')
        try:
            self.sock.close()
        except socket.error as e:
            print('ERROR in closing socket:\n{}'.format(e))
        print('Socket closed...')

    # Excute different functions according to service id
    def process_req(self, req, address):
        msg = unmarshal(req)
        service_id = msg[0]
        if service_id not in [1,2,3,4,5]: # Filter out invalid input
            raise ValueError("Received an invalid service id!")

        elif service_id == 1:  # Read content of file
            return self.read_file(msg[2], msg[3], msg[4])  # Parameters are: filename, offset, length

        elif service_id == 2:  # Insert content into file
            self.time = time.time()
            content = self.insert_content(msg[2], msg[3], msg[4])
            self.callback(content, msg)
            return content

        elif service_id == 3:  # Monitor updates made to specified file
            return self.monitorFile(msg[2], msg[3], address, msg[-1])  # Parameters are: filePathName, monitorInterval, address, opr

        elif service_id == 4:  # Get names of files under ./file, it is idempotent
            return self.collect_file_names()

        elif service_id == 5:  # Create a new file, it is non-idempotent(last modification time changes)
            return self.createFile(msg[2], msg[3])

    # Read files from local disk
    def read_file(self, file_name, offset, length):
        try:
            file_path = self.dictPath + file_name
            with open(file_path, "r") as f:
                content = f.read()
                file_len = len(content)
                # if offset exceeds the file length, reply an error message
                if offset >= file_len:
                    # [service_id, num_obj, msg_type, msg_ctnt]
                    return [1, 1, ERR, "Offset exceeds file length"]
                # else read from offset-th bytes by length bytes
                else:
                    f.seek(offset, 0)
                    content = f.read(int(length))
                    f.close()
                    return [1, 1, STR, content]
        except FileNotFoundError:
            return [1, 1, ERR, "ERROR: File does not exist on server"]
        except OSError as e:
            return [1, 1, ERR, str(e)]

    def insert_content(self, file_name, offset, length):
        try:
            file_path = self.dictPath + file_name
            with open(file_path, "r") as fr:
                content = fr.read()
                file_len = len(content)
                if offset >= file_len:
                    fr.close()
                    return [2, 1, ERR, "Offset exceeds file length"]
                fr.close()
            with open(file_path, "w") as fw:
                content = content[0:offset] + length + content[offset:]
                fw.write(content)
                fw.close()
                return [2, 2, FLT, STR, self.time, content]

        except FileNotFoundError:
            return [2, 1, ERR, "File does not exist on server"]
        except OSError as os_e:
            return [2, 1, ERR, str(os_e)]
        except Exception as e:
            return [2, 1, ERR, str(e)]

    def monitorFile(self, filePathName, monitorInterval, address, opr):
        try:
            fileName = self.dictPath + filePathName
            f = open(fileName, 'r')
            f.close()
        except FileNotFoundError:
            return [3, 1, ERR, "File does not exist on server"]

        if opr == ADD:
            if (address, filePathName) not in self.monitorList:
                self.monitorList.append((address, filePathName))
            print('{} added to the monitoring list for {} seconds for file: {}'.format(address, monitorInterval,                                                                       filePathName))
            print(self.monitorList)
            return [3, 1, STR, '{} added to the monitoring list for {} seconds for file: {}'.format(address, monitorInterval, filePathName)]
        if opr == REM:
            if (address, filePathName) in self.monitorList:
                self.monitorList.remove((address, filePathName))
            print('{} removed from monitoring list since monitor interval ended'.format(address))
            print(self.monitorList)
            return [3, 1, STR, '{} removed from monitoring list since monitor interval ended'.format(address)]

    # def countFile(self, filePathName):
    #     try:
    #         fileName = self.dictPath + filePathName
    #         f = open(fileName, 'r')
    #         count = len(f.read())
    #         f.close()
    #         return [4, 1, INT, count]
    #     except FileNotFoundError:
    #         return [4, 1, ERR, "File does not exist on server"]

    # Get names of files under ./file/
    def collect_file_names(self):
        file_names = []
        for root, dirs, files in os.walk(self.dictPath):
            for file in files:
                file_names.append(file)
        file_list = "\n".join(file_names)
        return [4,1,STR,file_list]

    def createFile(self, filePathName, char):
        try:
            fileName = self.dictPath + filePathName
            if os.path.exists(fileName):
                return [5, 1, ERR, 'File {} already exists, cannot create again.'.format(filePathName)]
            print(fileName)
            f = open(fileName, 'w')
            f.write(char)
            f.close()
            return [5, 1, STR, '{} file created in server.'.format(filePathName)]
        except Exception as e:
            return [5, 1, ERR, str(e)]

    def callback(self, content, d):
        if len(self.monitorList) > 0:   # Checks if there are clients registered for monitoring
            for i in self.monitorList:  # Loops through whole monitoring list
                if d[2] == i[1]:        # Checks if file is same as file registered for monitoring
                    print('Callback to {}: {}'.format(i[0], content))
                    self.sock.sendto(marshal(content), i[0])
        return

    def replyAtLeastOnce(self, data, address):
        reply = self.process_req(data, address)

        if self.simulateLoss and random.randrange(0, 10) > 4:
            self.sock.sendto(marshal(reply), address)
        elif self.simulateLoss is False:
            self.sock.sendto(marshal(reply), address)

    def replyAtMostOnce(self, data, address):
        # check server cache for existence of request
        # if found, reply client with cacheEntry
        for cacheEntry in self.cache:
            if cacheEntry[0] == [address[0], address[1], data]:
                if self.simulateLoss and random.randrange(0, 10) > 4:
                    self.sock.sendto(marshal(cacheEntry[1]), address)
                elif self.simulateLoss == False:
                    self.sock.sendto(marshal(cacheEntry[1]), address)
                return

        reply = self.process_req(data, address)

        if len(self.cache) == self.cacheLimit:
            self.cache = self.cache[1:]
        self.cache.append(([address[0], address[1], data], reply))

        if self.simulateLoss and random.randrange(0, 10) > 4:
            self.sock.sendto(marshal(reply), address)
        elif self.simulateLoss is False:
            self.sock.sendto(marshal(reply), address)


if __name__ == "__main__":
    parser = optparse.OptionParser()

    parser.add_option('-i', '--UDP_ip',
                      action="store", dest='UDP_ip',
                      help="Sets the ip address of the server", default="localhost")

    parser.add_option('-p', '--UDP_port',
                      action="store", dest="UDP_port",
                      help="Sets the port of server",
                      default=61032)

    parser.add_option('-s', '--invocationSemantics',
                      action="store", dest="invocationSemantics",
                      help="Sets the invocation semantics",
                      default='AT_LEAST_ONCE')
    parser.add_option('-l', '--simulateLoss',
                      action="store", dest="simulateLoss",
                      help="Sets the simulateLoss True or False",
                      default='False')
    
    options, args = parser.parse_args()
    server = Server(invocationSemantics1 = str(options.invocationSemantics),simulateLoss1 = bool(options.simulateLoss))
    server.UDP_ip = str(options.UDP_ip)
    server.UDP_port = int(options.UDP_port)
    server.invocationSemantics = str(options.invocationSemantics)
    server.run()
