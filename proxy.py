import sys
import socket
import time
from threading import Thread

class proxyServer:
    cache_responses = {}

    def __init__(self, port, listen_addr):
        self.port = port
        self.listen_addr = listen_addr
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.socket.bind((self.listen_addr, self.port))
        self.socket.listen(5)
        self.size = 4096
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.cache = True

    def recv_request(self, open_socket, timeout=1.0):
        open_socket.setblocking(0)
        parsed_headers = {}
        headers_expected = True
        data = []
        begin = time.time()
        while 1:
            if len(data) > 0 and time.time() - begin > timeout/3:
                break
            elif len(data) is 0 and time.time() - begin > timeout:
                break

            try:
                incoming_data = open_socket.recv(self.size)
                if incoming_data:
                    data.append(incoming_data)

                    # Parsing the headers
                    if headers_expected:
                        for line in incoming_data.split('\n'):
                            line = line.strip()
                            if line is "":
                                headers_expected = False
                                break
                            line = line.split(': ')
                            key = line[0].strip()
                            value = ''.join(line[1:]).strip()
                            if key is not "":
                                parsed_headers[key.lower()] = value

                    # Reset the waiting timeout
                    begin = time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        return ''.join(data), parsed_headers

    def fetch_from_server(self, raw_request, request):
        csock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        try:
            resolved_ip = socket.gethostbyname(request['hostname'])
        except:
            return {}, {}

        csock.connect((resolved_ip, int(request['port'])))

        filename = '/' + request['url'].split('/')[3]
        fl = raw_request.split('\n')[0]
        pr = fl.split()
        print pr
        pr[1] = filename
        fl = ' '.join(pr) + '\r'
        lines = raw_request.split('\n')
        lines[0] = fl
        newRequest = '\n'.join(lines) + '\n'

        csock.send(newRequest)
        response_data, response_headers = self.recv_request(csock)
        csock.close()
        return response_data, response_headers

    def fetchRequest(self, raw_request, request):
        if request['url'] in self.cache_responses:
            print "Found " + request['url'] + " in cache"
            return self.cache_responses[request['url']]
        else:
            response_data, response_headers = self.fetch_from_server(raw_request, request)

        print "Response Headers : \n", response_headers
        return response_data

    def listenThread(self, csock, addr):
        raw_request = csock.recv(self.size)
        print "raw request : \n%s" % raw_request
        request_header = raw_request.split('\n')[0].split()
        request = {}
        # request_header = raw_request[0].split();
        if len(request_header) >= 2:
            request['type'] = request_header[0]
            request['url'] = request_header[1]
            request['host'] = raw_request.split('\n')[1].split()[1]
        request['port'] = 80
        request['hostname'] = request['host'].split(':')[0]
        request['port'] = request['host'].split(':')[1]
        print request
        response = self.fetchRequest(raw_request, request)
        csock.send(str(response))

    def listenRequest(self):
        csock, addr = self.socket.accept()
        csock.settimeout(10)
        Thread(target=self.listenThread, args=(csock,addr)).start()

    def close(self):
        self.socket.close()

if __name__ == "__main__":
    port = 8080
    listen_addr = "127.0.0.1"
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        if len(sys.argv) > 2:
            listen_addr = sys.argv[2]
    server = proxyServer(port=port, listen_addr=listen_addr)
    while True:
        server.listenRequest()
    server.close()
