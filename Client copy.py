from Config import *
from Marshal import *
import os
import sys
import socket
import optparse
import time
import random

timeoutLimit = 1

class Client:

    def __init__(self):
        self.cache = [0, 0, '']  # cache = [Tvalid, Tclient, cacheEntry]
        self.HOST = 'localhost'
        self.PORT = 7777
        self.freshness_interval = 10
        self.simulateLoss = False


    def run(self):
        print('Starting client socket...')

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(timeoutLimit)
        except socket.error as e:
            print("Failed to create client socket:\n{}".format(e))
            sys.exit()

        while True:
            print('\n*****Function Menu of Remote File System*****')
            print('1: Read content of a file.')
            print('2: Insert content into a file.')
            print('3: Monitor updates of a file.')
            print('4: Check length of content in file.')
            print('5: Create a new file.')
            print('q: Quit the platform.\n')

            userChoice = input('Input 1 to 5 to achieve function or "q" to quit:')

            if userChoice == '1':
                filePathname = input('Input file path name:')
                offset = int(input('Input offset in bytes:'))
                numBytes = int(input('Input number of bytes:'))
                check = self.checkCache()
                if not check:
                    print('Retrieved from Cache: {}'.format(self.cache[-1]))
                else:
                    print('Server Reply: {}'.format(
                        self.queryRead(filePathname, offset, numBytes)[-1]))

            elif userChoice == '2':
                filePathname = input('Input file path name:')
                offset = int(input('Input offset in bytes:'))
                seq = input('Input sequence of bytes:')
                print('Server Reply: {}'.format(
                    self.queryInsert(filePathname, offset, seq)[-1]))

            elif userChoice == '3':
                filePathname = input('Input file path name:')
                monitorInterval = float(input('Input length of monitor interval in seconds:'))

                if monitorInterval < 0.0:
                    print('Monitor interval input invalid.')
                else:
                    # 发送消息建立第一次连接
                    reply = self.queryMonitor(filePathname, monitorInterval, ADD)[-1]
                    print('Server Reply: {}'.format(reply))
                    if reply != 'File does not exist on server':
                        timeStart = time.time()
                        updateTimes = 0
                        while monitorInterval > 0.0:
                            try:
                                self.sock.settimeout(monitorInterval)# 设置timeout 为计时时间
                                data, address = self.sock.recvfrom(4096) # 监视和等待返回的更新消息
                                update = unmarshal(data)[-1]
                                updateTimes += 1
                                print('{} times updating in {}:{}'.format(
                                    updateTimes,filePathname, update))
                                self.cache[-1] = update
                                # reduce time out
                                monitorInterval -= (time.time() - timeStart)
                            except socket.timeout:
                                # print(time.time() - timeStart)
                                # self.queryMonitor(filePathname, monitorInterval, ADD)
                                break
                        print(time.time() - timeStart)
                        self.sock.settimeout(timeoutLimit) # 恢复超时时间
                        self.queryMonitor(filePathname, monitorInterval, REM)
                        print('Monitoring of file "{}" ended with {} times change.'.format(filePathname,updateTimes))

            elif userChoice == '4':
                filePathname = input('Input file path name:')
                print('Server Reply: {} characters in {}'.format(
                    self.queryCount(filePathname)[-1], filePathname))

            elif userChoice == '5':
                fileName = input('Input file name:')
                char = str(input('Input file content:'))
                reply = self.queryCreate(fileName, char)[-1]
                print('Server Reply: {}'.format(reply))

            elif userChoice == 'q':
                self.close()
                break
            else:
                print('You have entered an incorrect service.')
                print('Please input a number from 1-5 or "q" to exit.\n')
        return

    def send(self, msg):
        while True:
            try:
                print(msg)
                # Simulate packet loss based on invocation scheme
                if self.simulateLoss and random.randrange(0, 2) == 0:
                    self.sock.sendto(marshal(msg), (self.HOST, self.PORT))
                elif self.simulateLoss == False:
                    self.sock.sendto(marshal(msg), (self.HOST, self.PORT))

                data, address = self.sock.recvfrom(4096)
                reply = unmarshal(data)
                if reply[0] == 0:
                    self.cache[1] = reply[-1]
                return reply
            except socket.timeout:
                print('Timeout')
            except Exception as e:
                print('Error occured while sending: {}'.format(e))

    def close(self):
        print('Closing socket...')
        try:
            self.sock.close()
        except socket.error as e:
            print('Error closing socket:\n{}'.format(e))
        print('Socket closed...')

    def queryRead(self, filePathname, offset, numBytes):
        item = self.send([1, 3, STR, INT, INT, filePathname, offset, numBytes])
        errors = ["File does not exist on server",
                  "Offset exceeds file length"]
        if item[-1] in errors:
            # to do list:delete from cache list
            self.cache[0], self.cache[1] = 0, 0
        else:
            self.cache[2] = item[-1]
        return item

    def queryInsert(self, filePathname, offset, seq):
        item = self.send([2, 3, STR, INT, STR, filePathname, offset, seq])
        errors = ["File does not exist on server",
                  "Offset exceeds file length"]
        if item[-1] not in errors:
            self.cache[-1], self.cache[1] = item[-1], item[-2]
        return item

    def queryMonitor(self, filePathname, monitorInterval, opr):
        item = self.send([3, 3, STR, FLT, INT, filePathname, monitorInterval, opr])
        print(item)
        return item

    def queryCount(self, filePathname):
        item = self.send([4, 1, STR, filePathname])
        return item

    def queryCreate(self, fileName, char):
        item = self.send([5, 2, STR, STR, fileName, char])
        return item

    def checkCache(self):
        Tvalid, Tclient = self.cache[0], self.cache[1]
        if self.cache == '':
            print('Cache entry empty. Send req to server')
            return True
        Tnow = time.time()

        if Tnow - Tvalid < self.freshness_interval:
            print('Does not need access to server, read from cache')
            return False
        elif Tnow - Tvalid >= self.freshness_interval:
            Tserver = self.send([0, 1, STR, 'Get Tserver'])[-1]  # fn to obtain Tserver
            self.cache[0] = Tnow
            if Tclient == Tserver:
                print('Cache entry valid. Data not modified at server.')
                return False
            elif Tclient < Tserver:
                print('Cache entry invalid. Send req to server')
                return True


if __name__ == "__main__":

    parser = optparse.OptionParser()

    parser.add_option('-t', '--freshness_interval',
                      action="store", dest="freshness_interval",
                      help='Sets the freshness interval of the client',
                      default=10
                      )

    parser.add_option('-i', '--ip_server',
                      action="store", dest="ip",
                      help='Sets the ip address of the server for client to send data to',
                      default='localhost'
                      )

    parser.add_option('-p', '--port',
                      action="store", dest="port",
                      help='Sets the port of the server for client to send data to',
                      default=7777
                      )

    options, args = parser.parse_args()

    client = Client()

    client.freshness_interval = options.freshness_interval
    client.PORT = int(options.port)
    client.HOST = str(options.ip)

    client.run()
