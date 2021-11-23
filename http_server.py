from threading import Thread
from queue import Queue
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


class Worker(Thread):
    def __init__(self, queue, request_handler, timeout):
        Thread.__init__(self)
        self.queue = queue
        self.handler = request_handler
        self.timeout = timeout

    def run(self):
        while True:
            client, add = self.queue.get()
            try:
                self.handle_client(client)
            except Exception as e:
                logging.info("Exception {} occurred at address {}".format(e, add))
            finally:
                self.queue.task_done()

    def parse_request(self, data, header_dict):
        request_data = data.splitlines()[0]
        request_data = request_data.rstrip('\r\n')
        method, req_file, req_version = request_data.split()
        req_file = req_file.split('?')[0].lstrip('/')
        logging.info("Request file is {}\n".format(req_file))

        if header_dict['bad_request']:
            method = 'bad_request'
        if not req_file:
            req_file = 'index.html'
        elif req_file and req_file[-1] == '/':
            req_file = ''.join([req_file, 'index.html'])
        return method, req_file

    def rebuild_header(self, data):
        field_dict = {}
        request_data = data.splitlines()
        for ln in request_data:
            item = ln.rstrip('\r\n')
            if not item:
                field_dict['end'] = True
            item_ = item.split(':', 1)
            if len(item_) == 2:
                field_dict[item_[0]] = item_[1]
        return field_dict

    def handle_client(self, client):
        buf = []
        buf_len = 0
        begin = time.time()
        header = {'end': False, 'bad_request': False}
        while True:
            if buf and time.time() - begin > self.timeout:
                break
            elif time.time() - begin > self.timeout * 2:
                break
            try:
                data_batch = client.recv(2048).decode('utf-8')
                if not header['end']:
                    upd_header = self.rebuild_header(data_batch)
                    header.update(upd_header)
                logging.info("Client's request header {}\n".format(header))
                if (header.get('Transfer-Encoding') and
                        header.get('Transfer-Encoding') != 'identity' and
                        len(data_batch) == 0):
                    break
                elif (not header.get('Transfer-Encoding') and
                      header.get('Content-Length') and
                      buf_len > 0 and
                      buf_len >= header.get('Content-Length')):
                    break
                elif not data_batch:
                    header['bad_request'] = True
                    break
                buf.append(data_batch)
                buf_len += len(data_batch)
                begin = time.time()
            except:
                pass

        logging.info("Client's request header {}\n".format(header))
        data = ''.join(buf)
        logging.info("Client's request is {}\n".format(data))
        if data:
            method, req_file = self.parse_request(data, header)
            response = self.handler(method, req_file)
            client.sendall(response)
        client.close()


class ThreadPool:
    def __init__(self, num_workers, handler, timeout):
        self.queue = Queue()
        self.num_workers = num_workers
        self.handler = handler
        self.timeout = timeout

    def build_worker_pool(self):
        for _ in range(self.num_workers):
            worker = Worker(self.queue, self.handler, self.timeout)
            worker.daemon = True
            worker.start()

    def add_task(self, *args):
        self.queue.put(args)

    def complete(self):
        self.queue.join()


class HTTPSever:

    def __init__(self, server_address, request_handler, workers):
        self.host = server_address[0]
        self.port = server_address[1]
        self.handler = request_handler
        self.workers_num = workers
        self.queue_lim = 128
        self.timeout = 0.01
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
        pool = ThreadPool(self.workers_num, self.handler, self.timeout)
        pool.build_worker_pool()

        while self.running_state:
            cl, adr = self.socket.accept()
            cl.settimeout(self.timeout)
            cl.setblocking(False)
            logging.info("Client with adress {i} has been connected at {p} port".format(i=adr[0], p=adr[1]))
            pool.add_task(cl, adr)
        pool.complete()
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
        elif method == 'bad_request':
            header = response_status_templ.format(400, 'Bad request').encode('utf-8')
            response = response_templ.format(400, 'Bad request').encode('utf-8')
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
