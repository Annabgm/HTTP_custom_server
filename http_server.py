from threading import Thread
import socket
from datetime import datetime
from optparse import OptionParser
import logging
import os
import sys
import re


def urldecode(file_name):
    p = re.compile(r'%\w{2}')
    symbols = p.split(file_name)
    special = p.findall(file_name)
    name = [symbols[0]]
    for i in range(len(symbols[1:])):
        name.append(bytearray.fromhex(special[i].lstrip('%')).decode())
        name.append(symbols[i + 1])
    return ''.join(name)


def define_type(file_name):
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


response_templ = '<html><body><center><h3>Error {0}: {1}</h3></center></body></html>'
response_status_templ = 'HTTP/1.1 {0} {1}\r\n'


class HTTPSever:

    def __init__(self, server_address, request_handler, workers):
        self.host = server_address[0]
        self.port = server_address[1]
        self.handler = request_handler
        self.workers_num = workers
        self.timeout = 5
        self.running_state = None
        self.service_state(True)
        self.socket = None

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
            self.close()

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def parse_request(self, data):
        request_data = data.splitlines()[0]
        request_data = request_data.rstrip('\r\n')
        method, req_file, req_version = request_data.split()
        req_file = req_file.split('?')[0].lstrip('/')
        logging.info("Request file is {}\n".format(req_file))

        if req_file == '/':
            req_file = 'index.html'
        elif req_file[-1] == '/':
            req_file = ''.join([req_file, 'index.html'])
        return method, req_file

    def handle_client(self, client, client_address):
        data = client.recv(2048).decode('utf-8')
        logging.info("Client's request is {}\n".format(data))
        logging.info("Client's address is {}\n".format(client_address[0]))
        if data:
            method, req_file = self.parse_request(data)
            response = self.handler(method, req_file)
            client.sendall(response)
        client.close()


class HTTPHandler:
    def __init__(self, dir_name):
        self._dir = dir_name

    def __call__(self, method, file_name):
        server_headers = [
            ('Server', 'OTUServer'),
            ('Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ('Connection', 'keep-alive')
        ]
        if method == 'GET':
            header, response = self.do_get(urldecode(file_name), server_headers)
        elif method == 'HEAD':
            header = self.do_head(file_name, server_headers)
            response = ''.encode('utf-8')
        else:
            header = response_status_templ.format(405, 'Not allowed').encode('utf-8')
            response = response_templ.format(405, 'Method not allowed').encode('utf-8')
        final_response = header + response
        return final_response

    def do_get(self, file_name, header):
        try:
            with open(os.path.join(self._dir, file_name), 'rb') as f:
                response = f.read()
            response_status = response_status_templ.format(200, 'OK')
            server_headers = [
                ('Content-Type', define_type(file_name)),
                ('Content-Length', str(len(response)))
            ]
            header = header + server_headers
        except FileNotFoundError:
            response_status = response_status_templ.format(404, 'Not Found')
            response = response_templ.format(404, 'File not found').encode('utf-8')
        except PermissionError:
            response_status = response_status_templ.format(403, 'Forbidden')
            response = response_templ.format(403, 'Access forbidden').encode('utf-8')
        for el in header:
            response_status += '{0}: {1}\r\n'.format(*el)
        response_status += '\r\n'
        logging.info("Response header is {}\n".format(response_status))
        response_header = response_status.encode('utf-8')
        return response_header, response

    def do_head(self, file_name, header):
        try:
            with open(os.path.join(self._dir, file_name), 'rb') as f:
                response = f.read()
            response_status = response_status_templ.format(200, 'OK')
            server_headers = [
                ('Content-Type', define_type(file_name)),
                ('Content-Length', str(len(response)))
            ]
            header = header + server_headers
        except:
            response_status = response_status_templ.format(404, 'Not Found')
        for el in header:
            response_status += '{0}: {1}\r\n'.format(*el)
        response_status += '\r\n'
        logging.info("Response header is {}\n".format(response_status))
        response_header = response_status.encode('utf-8')
        return response_header


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
