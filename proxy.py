import sys
import socket
import time
from threading import Thread
import base64

blackList = [('geeksforgeeks.com', '69.172.201.153/32'),('localhost','127.0.0.1/32')]
autherisedUsers = {
		"myName":"myPass",
		"myName2":"myPass2"
	}

class proxyServer:
    cache_responses = {}
    request_log = {}
    cache_log = {}

    def __init__(self, port, listen_addr):
        self.port = port
        self.listen_addr = listen_addr
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.socket.bind((self.listen_addr, self.port))
        self.socket.listen(5)
        self.size = 1024
        self.cache_size = 3
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.cache = True

    def recv_request(self, open_socket, timeout=1.0):
        open_socket.setblocking(0)
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
                    begin = time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        return ''.join(data)#, parsed_headers
   
    def userAuthentication(self, request):
	line3 = request.split('\n')[2]
	encodedb64 = line3.split(' ')[2]
	auth_string  = base64.b64decode(encodedb64)
	print('AUTH '+auth_string)
	auth_string  = auth_string.split(':')
	username = auth_string[0]
	password  = auth_string[1]
	if username in autherisedUsers.keys():
		if autherisedUsers[username]==password:
			return True
	return False
    def blacklisting(self, server, csock,request,authenticated):
	if authenticated:
		return False
    	print(request['hostname'])
	ip = request['hostname']
	cidr = str(ip)+'/32'
	if cidr in [x[1] for x in blackList]:
		print('HERE')
		#csock.send("This IP is blocked")
		#csock.close()
		return True
	return False

    def fetch_from_server(self, raw_request, request,csock):
	authenticated=self.userAuthentication(request)	
	if self.blacklisting(server,csock,request,authenticated):
		return "Blacklisten\n"
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
        response_data = self.recv_request(csock)
        # response_data, response_headers = self.recv_request(csock)
        csock.close()
        return response_data#, response_headers

    def is_cachable(self, request, response_headers):
        if len(response_headers) == 0:
            # Something bad happened with request, lets not cache it.
            return False
        if 'HTTP/1.0 200 OK' not in response_headers:
            return False
        if 'Cache-control' in response_headers:
            value = response_headers['Cache-control']
            if "private" in value or "no-cache" in value:
                return False
        if 'Pragma' in response_headers:
            value = response_headers['Pragma']
            if "private" in value or "no-cache" in value:
                return False
        if not request['url'] in self.request_log:
            return False
        if len(self.request_log[request['url']]) < 3:
            return False
        requestTime = time.mktime(time.strptime(self.request_log[request['url']][-3], "%a %b  %d %H:%M:%S %Z %Y"))
        if time.time() - requestTime > 300.0:
            return False
        return True

    def fetchRequest(self, raw_request, request,csock):
        if request['type'] == "GET" and request['url'] in self.cache_responses:
            print "Found " + request['url'] + " in cache"
            lines = raw_request.split('\n')
            # print lines
            lines[-2] = "If-Modified-Since: " + self.cache_log[request['url']] + "\r"
            lines.append("\r\n\r\n")
            raw_request = "\n".join(lines)
            # return self.cache_responses[request['url']]
        print "raw request : \n%s" % raw_request

        response_data = self.fetch_from_server(raw_request, request,csock)


        # response_data, response_headers = self.fetch_from_server(raw_request, request)

        # print "Response Headers : \n", response_headers
        print "Response Data : \n", response_data

        response_headers = {}
        response_headers[response_data.split('\n')[0].strip('\r')] = ''
        for line in response_data.split('\n'):
            if ':' in line:
                key = line.split(':')[0]
                value = line.split(':')[1].strip('\r')
                response_headers[key] = value

        if "HTTP/1.0 304 Not Modified" in response_headers:
            return self.cache_responses[request['url']]

        if request['type'] == "GET" and self.is_cachable(request, response_headers):
            print "Adding " + request['url'] + " to cache"
            if request['url'] in self.cache_responses:
                self.cache_responses[request['url']] = response_data
                self.cache_log[request['url']] = request['mtime']
            else:
                if len(self.cache_responses) < self.cache_size:
                    self.cache_responses[request['url']] = response_data
                    self.cache_log[request['url']] = request['mtime']
                else:
                    mtimes = []
                    for i in self.cache_log.values():
                        mtimes.append(time.strptime(i, "%a %b  %d %H:%M:%S %Z %Y"))
                    minTime = min(mtimes)
                    for url in self.cache_responses.keys():
                        if time.strptime(self.cache_log[url], "%a %b  %d %H:%M:%S %Z %Y") == minTime:
                            print "removing", url, "from cache"
                            del self.cache_responses[url]
                            del self.cache_log[url]
                    self.cache_responses[request['url']] = response_data
                    self.cache_log[request['url']] = request['mtime']
            print "Cache Size :", len(self.cache_responses)
        return response_data

    def listenThread(self, csock, addr):
        raw_request = csock.recv(self.size)
	print "RAW REQUEST", raw_request
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
        request['mtime'] = time.strftime("%a %b  %d %H:%M:%S %Z %Y", time.localtime())
        print request
        if not request['url'] in self.request_log:
            self.request_log[request['url']] = []
        self.request_log[request['url']].append(request['mtime'])
        print self.request_log
        response = self.fetchRequest(raw_request, request,csock)
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
