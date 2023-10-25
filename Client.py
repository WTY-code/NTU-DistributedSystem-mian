from Marshal import *
import sys
import socket
import optparse
import time
import random

timeoutLimit = 5


class Client:

    def __init__(self, host='localhost', port=61032, freshness_interval=6000000, simulateLoss1=False):
        self.HOST = host
        self.PORT = port
        self.freshness_interval = freshness_interval
        self.simulateLoss = simulateLoss1
        self.sock = None
        self.cache_list = {} # {filename1:(timelastread, content), filename2:(timelastread, content)}

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

    def read_file(self):
        file_name = input('Input file name:')
        start = int(input('Input offset in bytes:'))
        length = int(input('Input number of bytes:'))
        end = start + length -1
        if self.is_cache_valid(file_name, start, end):
            content = self.fetch_from_cache(file_name, start, end)
            print('Retrieved from Cache: {}'.format(content))
        else:
            server_message = self.queryRead(file_name, start, length)
            print('Server Reply: {}'.format(server_message[-1]))
        # is_cache_invalid = self.checkCache()
        # if not is_cache_invalid:
        #     print('Retrieved from Cache: {}'.format(self.cache[-1]))
        # else:
        #     server_message = self.queryRead(file_name, start, length)
        #     print('Server Reply: {}'.format(server_message[-1]))

    def add_content(self):
        file_name = input('Input file name:')
        byte_offset = int(input('Input offset in bytes:'))
        content_sequence = input('Input sequence of bytes:')
        server_response = self.queryInsert(file_name, byte_offset, content_sequence)
        print('Server Reply: {}'.format(server_response[-1]))
        # read your writes
        if file_name in self.cache_list:
            self.delete_cache(file_name)

        return

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
                        # server inform client updates, client make a cache
                        self.add_cache(file_path, time.time(), 0, len(alteration_details)-1, alteration_details)
                        # self.cache[-1] = alteration_details
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
                packet_loss_simulation = self.simulateLoss and random.randrange(0, 10) > 4
                if packet_loss_simulation or not self.simulateLoss:
                    packet = marshal(message)
                    self.sock.sendto(packet, (self.HOST, self.PORT))

                response_packet, server_address = self.sock.recvfrom(4096)
                response_message = unmarshal(response_packet)
                # if response_message[0] == 0:
                #     self.cache[1] = response_message[-1]
                return response_message
            except socket.timeout:
                print('Transmission delay exceeded. Retrying...')
            except Exception as transmission_issue:
                print('Transmission disruption: {}'.format(transmission_issue))

    def queryRead(self, filePathname, offset, numBytes):
        item = self.send([1, 3, STR, INT, INT, filePathname, offset, numBytes])
        errors = ["File does not exist on server",
                  "Offset exceeds file length"]
        # if item[-1] in errors:
        #     self.cache[0], self.cache[1] = 0, 0
        content = item[-1]
        if errors[0] in content:
            if filePathname in self.cache_list:
                self.delete_cache(filePathname)
        elif errors[1] in content:
            pass
        else:
            # self.cache[2] = item[-1]
            # read new file, make a cache entry and add it into cache list1
            start = offset
            self.add_cache(filePathname, time.time(), start, start + numBytes - 1, content)
            # cache_entry = {}
            # cache_entry["T_lastread"] = time.time()
            # cache_entry["start"] = offset
            # cache_entry["end"] = offset + numBytes - 1 # index of last char
            # cache_entry["content"] = item[-1]
            # self.cache_list[filePathname] = cache_entry
        return item

    def queryInsert(self, filePathname, offset, seq):
        item = self.send([2, 3, STR, INT, STR, filePathname, offset, seq])
        # errors = ["File does not exist on server",
        #           "Offset exceeds file length"]
        # if item[-1] not in errors:
        #     # 将读到的文件内容存入cache
        #     self.cache[-1], self.cache[1] = item[-1], item[-2]
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

    def within_cache_range(self, filename, start, end):
        if start >= self.cache_list[filename]["start"] \
                    and end <= self.cache_list[filename]["end"]:
            return True
        else:
            return False

    def within_freshness(self, filename):
        if (time.time() - self.cache_list[filename]["T_lastread"]) <= self.freshness_interval:
            return True
        else:
            return False


    def is_cache_valid(self, filename, start, end):
        # T_now = time.time()
        # filename i
        if filename in self.cache_list:
            if self.within_cache_range(filename, start, end) and self.within_freshness(filename):
                print("cache of {} is valid!".format(filename))
                return True
            elif not self.within_freshness(filename):
                self.delete_cache(filename)
        else:
            print("No cache entry.")
        return False

    def fetch_from_cache(self, filename, start, end):
        return self.cache_list[filename]["content"][start:(end+1)]

    def delete_cache(self, filename):
        try:
            del self.cache_list[filename]
            print("cache entry of {} should be refreshed, delete invalid entry.".format(filename))
        except Exception as e:
            print("ERROR in deleting cache entry of {}".format(filename))

    def add_cache(self, filename, T_lastread, start, end, content):
        cache_entry = {}
        cache_entry["T_lastread"] = T_lastread
        cache_entry["start"] = start
        cache_entry["end"] = end # index of last char
        cache_entry["content"] = content
        self.cache_list[filename] = cache_entry

    # def checkCache(self):
    #     cacheTimestamp, clientTimestamp = self.cache[0], self.cache[1]
    #     if self.cache == '':
    #         print('No cache data. Requesting from server.')
    #         return True
    #
    #     currentTimestamp = time.time()
    #     if currentTimestamp - cacheTimestamp < self.freshness_interval:
    #         print('Server access unnecessary, loading from cache.')
    #         return False
    #     else:
    #         serverTimestamp = self.send([0, 1, STR, 'Get Tserver'])[-1]  # Method to retrieve server time
    #         self.cache[0] = currentTimestamp
    #         if clientTimestamp == serverTimestamp:
    #             print('Cache is up-to-date. No server changes detected.')
    #             return False
    #         elif clientTimestamp < serverTimestamp:
    #             print('Outdated cache. Requesting update from server.')
    #             return True

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
            '1': self.read_file,
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
                      default=60000
                      )

    parser.add_option('-i', '--ip_server',
                      action="store", dest="ip",
                      help='Sets the ip address of the server for client to send data to',
                      default='localhost'
                      )

    parser.add_option('-p', '--port',
                      action="store", dest="port",
                      help='Sets the port of the server for client to send data to',
                      default=61032
                      )
    parser.add_option('-l', '--simulateLoss',
                      action="store", dest="simulateLoss",
                      help="Sets the simulateLoss True or False",
                      default='False')
    options, args = parser.parse_args()

    client = Client(host=options.ip, port=int(options.port), freshness_interval=options.freshness_interval,simulateLoss1 = bool(options.simulateLoss))

    client.mainLoop()
