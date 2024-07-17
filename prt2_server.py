import socket
import threading
import os

HEADER = 64
FORMAT = 'utf-8'
PORT = 1603
HOST = socket.gethostbyname(socket.gethostname())
FILE_LIST_PATH = 'file_list.txt'
DELIMITER = ' '

CHUNK_SIZE = 1024
PRIORITY = {
    "NORMAL": 1,
    "HIGH": 4,
    "CRITICAL": 10
}

def load_file_list():
    with open(FILE_LIST_PATH, 'r') as file:
        return file.read()

def file_exists(filename):
    with open(FILE_LIST_PATH, 'r') as file:
        file_list = [line.split()[0] for line in file.read().splitlines()]
    return filename in file_list and os.path.exists(FILE_LIST_PATH)

def apply_protocol(method, data):
    message = f"{method}{DELIMITER}{data}"
    message_encoded = message.encode(FORMAT)
    msg_length = len(message_encoded)
    header = f'HEAD {msg_length}'.encode(FORMAT)
    header += b' ' * (HEADER - len(header))
    protocol_message = header + message_encoded
    return protocol_message


def update_list(client, addr, download_list):
    while True:
        try:
            str_header = client.recv(HEADER).decode(FORMAT)
            if not str_header:
                break
            msg_length = int(str_header.split(DELIMITER)[1])
            message = client.recv(msg_length).decode(FORMAT)
            method, data = message.split(DELIMITER, 1)
            if method == "GET":
                filename, priority = data.split(DELIMITER)
                sent = 0
                if file_exists(filename):
                    client.sendall(apply_protocol("SEN", "OK" + DELIMITER + str(os.path.getsize(filename))))
                    download_list.append((filename, priority, sent))
                else:
                    print(f"[ERROR] {filename} requested from {addr} does not exist!")
                    client.send(apply_protocol("ERR", filename))
        except Exception as e: 
            print(f"Error {e}")
            continue

def process_list(client, addr, download_list):
    while True:
        try:
            for i in range(len(download_list)):
                filename, priority, sent = download_list[i]
                with open(filename, 'rb') as output:
                    output.seek(sent * CHUNK_SIZE)
                    priority = PRIORITY.get(priority, 0)
                    for _ in range(priority):
                        chunk = output.read(CHUNK_SIZE)
                        if not chunk:
                            client.sendall(apply_protocol("SEN","END"))
                            print(f"[SEND] Sent {filename} to {addr} successfully!")
                            download_list.pop(i)
                            i -= 1
                            break
                        client.sendall(apply_protocol("SEF", filename + DELIMITER + chunk))
                    
        except Exception as e: 
            print(f"Error {e}")
            continue


def handle_client(client, addr):
    print(f"[NEW CONNECTION] A new connection is accepted from {addr}")
    file_list = load_file_list()
    client.sendall(apply_protocol("SEN", file_list))
    download_list = []
    while True:
        try:
            list_process = threading.Thread(target=process_list,args=(client, addr, download_list))
            list_update = threading.Thread(target=update_list,args=(client, addr, download_list))
            list_process.start()
            list_update.start()
        except Exception as e:
            print(f"Error: {e}")
            break
    print(f"[DISCONNECTED] {addr} has disconnected!")
    client.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server is listening on {HOST}:{PORT}")
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
