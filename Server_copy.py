import os

from Marshal import *
from Config import *
import socket
import time
import sys
import random
import optparse


class Server:
    def __init__(self):
        self.UDP_ip = "localhost"#"10.241.239.157"
        self.UDP_port = 7777
        self.time = time.time()
        self.cache = []
        self.cacheLimit = 10
        self.monitorList = []  # monitoring list format: [address, filePathname]
        self.invocationSemantics = 'AT_LEAST_ONCE'
        self.simulateLoss = True
        self.dictPath = './file/'
        self.dict = 'file'
        # create file dictionary
        if not os.path.exists(self.dict):
            os.mkdir(self.dict)

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET,  # Internet
                                      socket.SOCK_DGRAM)  # UDP
        except socket.error as e:
            print('Failed to create socket:\n{}'.format(e))
            sys.exit()

        # bind socket to port
        serverAddress = (self.UDP_ip, self.UDP_port)
        print('Starting server on {} Port {}...'.format(
            self.UDP_ip, self.UDP_port))

        print('Invocation semantics used: {}'.format(self.invocationSemantics))

        try:
            self.sock.bind(serverAddress)
        except socket.error as e:
            print('Socket bind failed:\n{}'.format(e))
            sys.exit()


        # once socket bind, keep talking to client
        self.wait_for_req()

    # await data from client
    def wait_for_req(self):
        while True:
            #print('Monitor List: {}'.format(self.monitorList))
            print('Server is waiting for request from client...')
            msg, address = self.sock.recvfrom(SOCK_MAX)
            print(msg)
            print('Received request message from {}:\n{!r}'.format(address, msg))
            self.reply(msg, address)

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

    def process_req(self, req, address):
        msg = unpack(req)  # unpacked data as variable, msg
        service_id = msg[0]
        if service_id not in [0,1,2,3,4,5]:
            raise ValueError("Received an invalid service id!")

        elif service_id == 0:
            return self.reply_server_time()

        elif service_id == 1:  # Read content of file

            return self.read_file(msg[2], msg[3], msg[4])

        elif service_id == 2:  # Insert content into file
            self.time = time.time()
            content = self.insert_content(msg[2], msg[3], msg[4])
            self.callback(content, msg)
            return content

        elif service_id == 3:  # Monitor updates made to content of specified file
            return self.monitorFile(msg[2], msg[3], address, msg[-1])

        elif service_id == 4:  # Count content in file
            return self.countFile(msg[2])

        elif service_id == 5:  # Create a new file
            return self.createFile(msg[2], msg[3])

    def reply_server_time(self):
        return [0, 1, FLT, self.time]

    def read_file(self, file_name, offset, length):
        try:
            file_path = self.dictPath + file_name
            with open(file_path, "r") as f:
                content = f.read()
                file_len = len(content)
                if offset >= file_len:
                    return [1, 1, ERR, "Offset exceeds file length"]
                else:
                    f.seek(offset, 0)
                    content = f.read(int(length))
                    f.close()
                    return [1, 1, STR, content]
        except FileNotFoundError:
            return [1, 1, ERR, "ERROR: File does not exist!"]
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
        except OSError as e:
            return [2, 1, ERR, str(e)]
        except Exception as other_e:
            return [2, 1, ERR, str(other_e)]

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

    def countFile(self, filePathName):
        try:
            fileName = self.dictPath + filePathName
            f = open(fileName, 'r')
            count = len(f.read())
            f.close()
            return [4, 1, INT, count]
        except FileNotFoundError:
            return [4, 1, ERR, "File does not exist on server"]

    def createFile(self, filePathName, char):
        try:
            fileName = self.dictPath + filePathName
            print(fileName)
            f = open(fileName, 'w')
            f.write(char)
            f.close()
            return [5, 1, STR, '{} file created in server.'.format(filePathName)]
        except Exception as e:
            return [5, 1, ERR, str(e)]

    def callback(self, content, d):
        if len(self.monitorList) > 0:  # Checks if there are clients registered for monitoring
            for i in self.monitorList:  # Loops through whole monitoring list
                if d[2] == i[1]:  # Checks if file is same as file registered for monitoring
                    print('Callback to {}: {}'.format(i[0], content))
                    self.sock.sendto(pack(content), i[0])
        return

    def replyAtLeastOnce(self, data, address):
        reply = self.process_req(data, address)

        if self.simulateLoss and random.randrange(0, 2) == 0:
            self.sock.sendto(pack(reply), address)
        elif self.simulateLoss == False:
            self.sock.sendto(pack(reply), address)

    def replyAtMostOnce(self, data, address):
        # check server cache for existence of request
        # if found, reply client with cacheEntry
        for cacheEntry in self.cache:
            if cacheEntry[0] == [address[0], address[1], data]:
                if self.simulateLoss and random.randrange(0, 2) == 0:
                    self.sock.sendto(pack(cacheEntry[1]), address)
                elif self.simulateLoss == False:
                    self.sock.sendto(pack(cacheEntry[1]), address)
                return

        reply = self.process_req(data, address)

        if len(self.cache) == self.cacheLimit:
            self.cache = self.cache[1:]
        self.cache.append(([address[0], address[1], data], reply))

        if self.simulateLoss and random.randrange(0, 2) == 0:
            self.sock.sendto(pack(reply), address)
        elif self.simulateLoss == False:
            self.sock.sendto(pack(reply), address)


if __name__ == "__main__":
    parser = optparse.OptionParser()

    parser.add_option('-i', '--UDP_ip',
                      action="store", dest='UDP_ip',
                      help="Sets the ip address of the server", default="localhost")

    parser.add_option('-p', '--UDP_port',
                      action="store", dest="UDP_port",
                      help="Sets the port of server",
                      default=7777)

    parser.add_option('-s', '--invocationSemantics',
                      action="store", dest="invocationSemantics",
                      help="Sets the invocation semantics",
                      default='AT_LEAST_ONCE')

    server = Server()
    options, args = parser.parse_args()
    server.UDP_ip = str(options.UDP_ip)
    server.UDP_port = int(options.UDP_port)
    server.invocationSemantics = str(options.invocationSemantics)
    server.run()
