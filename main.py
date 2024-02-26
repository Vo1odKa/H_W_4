from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib
import json
import socket
import threading
from datetime import datetime

class CustomHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        elif pr_url.path == '/style.css':
            self.send_static()
        elif pr_url.path == '/logo.png':
            self.send_static()
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def do_POST(self):
        pr_url = urllib.parse.urlparse(self.path)

        if pr_url.path == '/message':
            content_length = int(self.headers['Content-Length'])
            data = self.rfile.read(content_length).decode('utf-8')
            form_data = urllib.parse.parse_qs(data)

            username = form_data.get('username', [''])[0]
            email = form_data.get('email', [''])[0]
            message = form_data.get('message', [''])[0]

            self.forward_to_socket_server({
                'username': username,
                'email': email,
                'message': message
            })

            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Не знайдено".encode('utf-8'))

    def forward_to_socket_server(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            server_address = ('localhost', 5000)
            s.sendto(json.dumps(data).encode('utf-8'), server_address)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())

class SocketServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('localhost', 5000))
            while True:
                data, addr = s.recvfrom(1024)
                data_dict = json.loads(data.decode('utf-8'))
                self.save_to_json(data_dict)

    
    def save_to_json(self, data_dict):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        with open('storage/data.json', 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = {}

        # Додаємо дані форми до словника
        form_data = {
            'timestamp': timestamp,
            'username': data_dict.get('username', ''),
            'email': data_dict.get('email', ''),
            'message': data_dict.get('message', '')
        }

        data[timestamp] = form_data

        with open('storage/data.json', 'w') as file:
            json.dump(data, file, indent=2)
def run_servers():
    print("Starting servers...")
    http_server = HTTPServer(('localhost', 3000), CustomHTTPHandler)
    socket_server = SocketServer()

    http_thread = threading.Thread(target=http_server.serve_forever)
    socket_thread = threading.Thread(target=socket_server.run)

    http_thread.daemon = True
    socket_thread.daemon = True

    http_thread.start()
    socket_thread.start()

    print("Servers started.")
    http_thread.join()
    socket_thread.join()
    print("Servers stopped.")

if __name__ == '__main__':
    run_servers()
