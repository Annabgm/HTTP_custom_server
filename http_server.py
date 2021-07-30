from threading import Thread, Event
import socket
from datetime import datetime
from optparse import OptionParser
import logging
import os
import sys
import re


class HTTPSever:

    def __init__(self, server_address, request_handler, workers):
        self.host = server_address[0]
        self.port = server_address[1]
        self.handler = request_handler
        self.workers_num = workers
        self.timeout = 5
        self.service_state(True)
        self._stop_event = Event()

    def service_state(self, state):
        self.running_state = state

    def run(self):
        try:
            logging.info("Defining Socket Server")
            self.socket = socket.socket(socket.AF_INET,
                                        socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            logging.info("Binding socket {h} {p}".format(h=self.host, p=self.port))
            self.socket.bind((self.host, self.port))
            logging.info("Date {}".format(datetime.now()))
            logging.info("Socket created successfully.")
        except:
            logging.error("Socket Creation Failed: " + str(sys.exc_info()))
            self.close()
            sys.exit()

        self.socket.listen(self.workers_num)
        logging.info("Socket now listening at {p}".format(p=self.port))

        while self.running_state:
            cl, adr = self.socket.accept()
            cl.settimeout(self.timeout)
            logging.info("Client {i} has been connected at {p} port".format(i=adr[0], p=adr[1]))
            t = Thread(target=self.handle_client, args=(cl, adr))
            t.start()
            t.join()
        self.close()
        print("Socket server has stopped")

    def stop_service(self, stop=False):
        if stop and self.running_state:
            logging.info("Service has been marked for shutdown")
            self.service_state(False)
            # self._stop_event.set()
            self.close()

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def handle_client(self, client, client_address):
        data = client.recv(2048).decode('utf-8')
        logging.info("Client's request is {}\n".format(data))
        logging.info("Client's address is {}\n".format(client_address[0]))
        if data:
            request_data = data.split(' ')
            method, req_file = request_data[0], request_data[1]
            req_file = req_file.split('?')[0].lstrip('/')
            logging.info("Request file is {}\n".format(req_file))
            
            if req_file == '/':
                req_file = 'index.html'
            elif req_file[-1] == '/':
                req_file = ''.join([req_file, 'index.html'])
            logging.info("Request file to response is {}\n".format(req_file))
            response = self.handler(method, req_file)
            client.sendall(response)
        client.close()


class HTTPHandler:
    def __init__(self, dir):
        self._dir = dir

    def __call__(self, method, file_name):
        server = 'Server: OTUServer\r\n'
        date = 'Date: {}\r\n'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        connection = 'Connection: keep-alive\r\n\r\n'
        if method == 'GET':
            header, response = self.do_GET(self.urldecode(file_name))
        elif method == 'HEAD':
            header = self.do_HEAD(file_name)
            response = ''.encode('utf-8')
        else:
            header = 'HTTP/1.1 405 Not allowed\n'.encode('utf-8')
            response = '<html><body><center><h3>Error 405: Method not allowed</h3></center></body></html>'.encode(
                'utf-8')
        const_response = ''.join([server, date, connection]).encode('utf-8')
        final_response = header + const_response + response
        return final_response

    def urldecode(self, file_name):
        p = re.compile(r'\%\w{2}')
        symbols = p.split(file_name)
        special = p.findall(file_name)
        name = [symbols[0]]
        for i in range(len(symbols[1:])):
            name.append(bytearray.fromhex(special[i].lstrip('%')).decode())
            name.append(symbols[i+1])
        return ''.join(name)


    def do_GET(self, file_name):
        try:
            with open(os.path.join(self._dir, file_name), 'rb') as f:
                response = f.read()
            status = 'HTTP/1.1 200 OK\r\n'
            content_type = 'Content-Type: {}\r\n'.format(self.define_type(file_name))
            content_length = 'Content-Length: {}\r\n'.format(len(response))
            header = ''.join([status, content_type, content_length])
            logging.info("Response body is {}\n".format(response))
        except FileNotFoundError:
            header = 'HTTP/1.1 404 Not Found\r\n'
            response = '<html><body><center><h3>Error 404: File not found</h3></center></body></html>'.encode(
                'utf-8')
        except PermissionError:
            header = 'HTTP/1.1 403 Forbidden\r\n'
            response = '<html><body><center><h3>Error 403: Access forbidden</h3></center></body></html>'.encode(
                'utf-8')
        logging.info("Response header is {}\n".format(header))
        header = header.encode('utf-8')
        return header, response

    def do_HEAD(self, file_name):
        try:
            with open(os.path.join(self._dir, file_name), 'rb') as f:
                response = f.read()
            status = 'HTTP/1.1 200 OK\r\n'
            content_type = 'Content-Type: {}\r\n'.format(self.define_type(file_name))
            content_length = 'Content-Length: {}\r\n'.format(len(response))
            header = ''.join([status, content_type, content_length])
        except:
            header = 'HTTP/1.1 404 Not Found\n'
        logging.info("Response header is {}\n".format(header))
        header = header.encode('utf-8')
        return header

    def define_type(self, file_name):
        if file_name.endswith(".html"):
            mimetype = 'text/html'
        elif file_name.endswith(".css"):
            mimetype = 'text/css'
        elif file_name.endswith(".js"):
            mimetype = 'text/javascript'
        elif file_name.endswith(".jpg") or file_name.endswith(".jpeg"):
            mimetype = 'image/jpeg'
        elif file_name.endswith(".png"):
            mimetype = 'image/png'
        elif file_name.endswith(".gif"):
            mimetype = 'image/gif'
        elif file_name.endswith(".swf"):
            mimetype = 'application/x-shockwave-flash'
        else:
            mimetype = 'text/plain'
        return mimetype


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-w", "--workers", action="store", type=int, default=5)
    op.add_option("-r", "--directory", action="store", default=None)
    (opts, args) = op.parse_args()
    print(opts)
    logging.basicConfig(filename='./log_parser.log', level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    serv = HTTPSever(("localhost", 8080), HTTPHandler(opts.directory), opts.workers)
    try:
        serv.run()
    except KeyboardInterrupt:
        logging.info("Keyboard shutdown. Server is closing.")
        serv.stop_service(True)
        sys.exit()
