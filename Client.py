from Marshal import *
import sys
import socket
import optparse
import time
import random

timeoutLimit = 1


class Client:

    def __init__(self, host='localhost', port=7777, freshness_interval=10, simulateLoss=False):
        self.cache = [0, 0, '']
        self.HOST = host
        self.PORT = port
        self.freshness_interval = freshness_interval
        self.simulateLoss = simulateLoss
        self.sock = None

    def startSocket(self):
        print('Starting client socket...')
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(timeoutLimit)
        except socket.error as e:
            print(f"Failed to create client socket:\n{e}")
            sys.exit()

    def closeSocket(self):
        print('Closing socket...')
        try:
            self.sock.close()
        except socket.error as e:
            print(f'Error closing socket:\n{e}')
        print('Socket closed...')

    def fetch_file(self):
        file_identifier = input('Input file path name:')
        start = int(input('Input offset in bytes:'))
        length = int(input('Input number of bytes:'))
        is_cache_invalid = self.checkCache()
        if not is_cache_invalid:
            print('Retrieved from Cache: {}'.format(self.cache[-1]))
        else:
            server_message = self.queryRead(file_identifier, start, length)
            print('Server Reply: {}'.format(server_message[-1]))

    def add_content(self):
        file_path = input('Input file path name:')
        byte_offset = int(input('Input offset in bytes:'))
        content_sequence = input('Input sequence of bytes:')
        server_response = self.queryInsert(file_path, byte_offset, content_sequence)
        print('Server Reply: {}'.format(server_response[-1]))

    def monitorFile(self):
        file_path = input('Input file path name:')
        tracking_period = float(input('Input length of monitor interval in seconds:'))

        if tracking_period < 0.0:
            print('Invalid duration for monitoring.')
        else:
            # Establish initial connection by sending a message
            initial_response = self.initiateMonitoring(file_path, tracking_period, ADD)[-1]
            print('Server Response: {}'.format(initial_response))
            if initial_response != 'File does not exist on server':
                observation_commencement = time.time()
                alteration_count = 0
                while tracking_period > 0.0:
                    try:
                        self.sock.settimeout(tracking_period)  # Adjust timeout to tracking period
                        packet, server_addr = self.sock.recvfrom(4096)  # Await update notifications
                        alteration_details = unmarshal(packet)[-1]
                        alteration_count += 1
                        print('Alteration #{0} in {1}: {2}'.format(
                            alteration_count, file_path, alteration_details))
                        self.cache[-1] = alteration_details
                        # Decrement remaining monitor interval
                        tracking_period -= (time.time() - observation_commencement)
                    except socket.timeout:
                        break  # Exit loop on timeout
                print('Elapsed time: ', time.time() - observation_commencement)
                self.sock.settimeout(timeoutLimit)  # Reset to default timeout
                self.initiateMonitoring(file_path, tracking_period, REM)
                print('Monitoring concluded for "{}" with {} alterations.'.format(file_path, alteration_count))


    def check_file_list(self):
        print('check server file list:')
        server_feedback = self.queryFileList()
        print('Server File List:\n{}'.format(server_feedback[-1]))

    def tally_file_characters(self):
        path_to_file = input('Input file path name:')
        server_feedback = self.queryCount(path_to_file)
        print('Server Reply: {} characters in {}'.format(server_feedback[-1], path_to_file))

    def createFile(self):
        designated_filename = input('Input file name:')
        content_input = str(input('Input file content:'))
        response = self.queryCreate(designated_filename, content_input)[-1]
        print('Server Reply: {}'.format(response))

    def invalidInput(self):
        print('Invalid input. Please enter a number from 1-5 or "q" to exit.\n')

    def send(self, message):
        transmission_in_progress = True
        while transmission_in_progress:
            try:
                print(message)
                # Introduce potential packet loss for simulation purposes
                packet_loss_simulation = self.simulateLoss and random.randint(0, 2) == 0
                if packet_loss_simulation or not self.simulateLoss:
                    packet = marshal(message)
                    self.sock.sendto(packet, (self.HOST, self.PORT))

                response_packet, server_address = self.sock.recvfrom(4096)
                response_message = unmarshal(response_packet)
                if response_message[0] == 0:
                    self.cache[1] = response_message[-1]
                return response_message
            except socket.timeout:
                print('Transmission delay exceeded. Retrying...')
            except Exception as transmission_issue:
                print('Transmission disruption: {}'.format(transmission_issue))

    def queryRead(self, filePathname, offset, numBytes):
        item = self.send([1, 3, STR, INT, INT, filePathname, offset, numBytes])
        errors = ["File does not exist on server",
                  "Offset exceeds file length"]
        if item[-1] in errors:
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

    def initiateMonitoring(self, filePathname, monitorInterval, opr):
        item = self.send([3, 3, STR, FLT, INT, filePathname, monitorInterval, opr])
        print(item)
        return item

    def queryCount(self, filePathname):
        item = self.send([4, 1, STR, filePathname])
        return item

    def queryFileList(self):
        item = self.send([4,0])
        return item

    def queryCreate(self, fileName, char):
        item = self.send([5, 2, STR, STR, fileName, char])
        return item

    def checkCache(self):
        cacheTimestamp, clientTimestamp = self.cache[0], self.cache[1]
        if self.cache == '':
            print('No cache data. Requesting from server.')
            return True

        currentTimestamp = time.time()
        if currentTimestamp - cacheTimestamp < self.freshness_interval:
            print('Server access unnecessary, loading from cache.')
            return False
        else:
            serverTimestamp = self.send([0, 1, STR, 'Get Tserver'])[-1]  # Method to retrieve server time
            self.cache[0] = currentTimestamp
            if clientTimestamp == serverTimestamp:
                print('Cache is up-to-date. No server changes detected.')
                return False
            elif clientTimestamp < serverTimestamp:
                print('Outdated cache. Requesting update from server.')
                return True

    def showMenu(self):
        print('\n*****Function Menu of Remote File System*****')
        print('1: Read content of a file.')
        print('2: Insert content into a file.')
        print('3: Monitor updates of a file.')
        # print('4: Check length of content in file.')
        print('4: Check File List.')
        print('5: Create a new file.')
        print('q: Quit the platform.\n')

    def mainLoop(self):
        self.startSocket()

        while True:
            self.showMenu()
            userChoice = input('Select an option (1-5 or "q" to quit): ')
            if userChoice == 'q':
                break

            action = self.getAction(userChoice)
            if action:
                action()

        self.closeSocket()

    def getAction(self, choice):
        actions = {
            '1': self.fetch_file,
            '2': self.add_content,
            '3': self.monitorFile,
            '4': self.check_file_list,# self.tally_file_characters,
            '5': self.createFile
        }
        return actions.get(choice, self.invalidInput)


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

    client = Client(host=options.ip, port=int(options.port), freshness_interval=options.freshness_interval)

    client.mainLoop()
