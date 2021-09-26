from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from optparse import OptionParser
from urllib import parse
from pathlib import Path
import socket
import logging
import os
import sys
import time
import mimetypes


mimetypes.add_type("application/javascript", ".js")
response_templ = '<html><body><center><h3>Error {0}: {1}</h3></center></body></html>'
response_status_templ = 'HTTP/1.1 {0} {1}\r\n'


class HTTPSever:

    def __init__(self, server_address, request_handler, workers):
        self.host = server_address[0]
        self.port = server_address[1]
        self.handler = request_handler
        self.workers_num = workers
        self.queue_lim = 128
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

        self.socket.listen(self.queue_lim)
        logging.info("Socket now listening at {p}".format(p=self.port))

        while self.running_state:
            cl, adr = self.socket.accept()
            cl.settimeout(self.timeout)
            cl.setblocking(0)
            logging.info("Client with adress {i} has been connected at {p} port".format(i=adr[0], p=adr[1]))
            with ThreadPoolExecutor(max_workers=self.workers_num) as executor:
                executor.submit(self.handle_client, cl)
            # t = Thread(target=self.handle_client, args=(cl, adr))
            # t.start()
            # t.join()
        self.close()
        logging.info("Socket server has stopped")

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

        if not req_file:
            req_file = 'index.html'
        elif req_file and req_file[-1] == '/':
            req_file = ''.join([req_file, 'index.html'])
        return method, req_file

    def handle_client(self, client):
        buf = []
        begin = time.time()
        while True:
            if buf and time.time()-begin > self.timeout:
                break
            elif time.time()-begin > self.timeout*2:
                break
            try:
                data_batch = client.recv(2048).decode('utf-8')
                if not data_batch:
                    break
                buf.append(data_batch)
                begin = time.time()
            except:
                pass

        data = ''.join(buf)
        # data = client.recv(2048).decode('utf-8')
        logging.info("Client's request is {}\n".format(data))
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
        file_name_parts = Path(self._dir).joinpath(file_name).absolute().parts
        doc_root = self._dir.split('/')[-1]
        if doc_root not in file_name_parts:
            header = response_status_templ.format(403, 'Forbidden').encode('utf-8')
            response = response_templ.format(403, 'Access forbidden').encode('utf-8')
        elif method == 'GET':
            header, response = self.do_get(parse.unquote(file_name), server_headers)
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
                ('Content-Type', mimetypes.guess_type(file_name, strict=False)[0]),
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
            resp_len = os.stat(os.path.join(self._dir, file_name)).st_size
            response_status = response_status_templ.format(200, 'OK')
            server_headers = [
                ('Content-Type', mimetypes.guess_type(file_name, strict=False)[0]),
                ('Content-Length', str(resp_len))
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
