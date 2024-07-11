import socket
import threading
import os
import sys

HEADER = 64
FORMAT = 'utf-8'
CHUNKS_SIZE = 1024
PORT = 1603
HOST = socket.gethostbyname(socket.gethostname())
FILE_LIST_PATH = 'file_list.txt'

def load_file_list():
    with open(FILE_LIST_PATH, 'r') as file:
        return file.read()

def is_exists(filename):
    with open(FILE_LIST_PATH, 'r') as file:
        file_list = [line.split()[0] for line in file.read().splitlines()]
    return filename in file_list and os.path.exists(FILE_LIST_PATH)

def create_protocol(method, filename):
    delimiter = ' '
    message = f"{method}{delimiter}{filename}"
    message_encoded = message.encode(FORMAT)
    msg_length = len(message_encoded)
    header = str(msg_length).encode(FORMAT)
    header += b' ' * (HEADER - len(header))
    protocol_message = header + message_encoded
    return protocol_message


def handle_client(client, addr):
    print(f"[NEW CONNECTION] A new connection is accepted from {addr}")
    file_list = load_file_list()
    client.sendall(file_list.encode())
    while True:
        str_header = client.recv(HEADER).decode(FORMAT)
        if not str_header:
            break
        header = int(str_header)
        message = client.recv(header).decode(FORMAT)
        msg_parts = message.split()
        method = msg_parts[0]
        filename = msg_parts[1]

        if len(msg_parts) == 2:
            if method == "GET":
                if is_exists(filename):
                    client.send(create_protocol("OK", filename))
                    with open(filename, 'rb') as output:
                        chunks = output.read(CHUNKS_SIZE)
                        while chunks:
                            client.sendall(chunks)
                            chunks = output.read(CHUNKS_SIZE)
                else:
                    client.send(create_protocol("ERR", filename))

            elif method == "DIS":
                break
    client.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server is listening on {HOST}:{PORT}")
        while True:
            client, addr = server.accept()
            client_handler = threading.Thread(target=handle_client, args=(client, addr))
            client_handler.start()


if __name__ == "__main__":
    print("Server is starting....")
    start_server()