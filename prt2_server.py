import queue
import socket
import threading
import os
import sys

HEADER = 64
FORMAT = 'utf-8'
PORT = 1603
HOST = socket.gethostbyname(socket.gethostname())
FILE_LIST_PATH = 'file_list.txt'
DELIMITER = ' '

CHUNKS_SIZE = 1024
NORMAL = 1
HIGH = 4 * NORMAL
CRITICAL = 10 * NORMAL

stop_event = threading.Event()

def load_file_list():
    with open(FILE_LIST_PATH, 'r') as file:
        return file.read()

def is_exist(filename):
    with open(FILE_LIST_PATH, 'r') as file:
        file_list = [line.split()[0] for line in file.read().splitlines()]
    return filename in file_list and os.path.exists(FILE_LIST_PATH)

def create_protocol(method, data):
    message = f"{method}{DELIMITER}{data}"
    message_encoded = message.encode(FORMAT)
    msg_length = len(message_encoded)
    header = f'HEAD {msg_length}'.encode(FORMAT)
    header += b' ' * (HEADER - len(header))
    protocol_message = header + message_encoded
    return protocol_message

download_queue = queue.Queue()
def update_queue(client, file_list):
    for file in file_list.splitlines():
        filename, priority = file.split()
        download_queue.put((client, filename, priority))

def handle_queue():
    while not stop_event.is_set():
        try:
            client, filename, priority = download_queue.get(timeout=2)
        except queue.Empty:
            continue
        if is_exist(filename):
            client.sendall(create_protocol("SEN", "OK"))
            with open(filename, 'rb') as output:
                chunks = output.read(CHUNKS_SIZE)
                while chunks:
                    for _ in range(globals()[priority]):
                        if not chunks:
                            break
                        client.sendall(create_protocol("PROC",chunks))
                        chunks = output.read(CHUNKS_SIZE)
                client.sendall(create_protocol("END",""))
        else:
            client.send(create_protocol("ERR", filename))


def handle_client(client, addr):
    print(f"[NEW CONNECTION] A new connection is accepted from {addr}")
    file_list = load_file_list()
    client.sendall(create_protocol("SEN", file_list))
    while True:
        try:
            str_header = client.recv(HEADER).decode(FORMAT)
            if not str_header:
                break
            msg_length = int(str_header.split(DELIMITER)[1])
            message = client.recv(msg_length).decode(FORMAT)
            method, data = message.split(DELIMITER, 1)
            if method == "DIS":
                stop_event.set()
                break
            if method == "GET":
                data = data.strip(DELIMITER)
                update_queue(client, data)

        except Exception as e:
            print(f"Error: {e}")
            break
    client.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server is listening on {HOST}:{PORT}")
        queue_handler = threading.Thread(target=handle_queue)
        queue_handler.start()
        try:
            while True:
                client, addr = server.accept()
                client_handler = threading.Thread(target=handle_client, args=(client, addr))
                client_handler.start()
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    print("Server is starting....")
    start_server()
