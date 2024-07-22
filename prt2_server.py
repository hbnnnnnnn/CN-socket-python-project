import socket
import threading
import os

HEADER = 64
FORMAT = 'utf-8'
PORT = 1603
HOST = socket.gethostbyname(socket.gethostname())
FILE_LIST_PATH = "file_list.txt"
DELIMITER = ' '

CHUNK_SIZE = 1024
PRIORITY = {
    "NORMAL": 1,
    "HIGH": 4,
    "CRITICAL": 10
}

def load_file_list():
    if os.path.exists(FILE_LIST_PATH):
        with open(FILE_LIST_PATH, 'r') as file:
            return file.read()

def file_exists(filename):
    if not os.path.exists(FILE_LIST_PATH):
        return False

    with open(FILE_LIST_PATH, 'r') as file:
        file_list = [line.split()[0] for line in file.read().splitlines()]

    return filename in file_list

def apply_protocol(method, data):
    message = f"{method}{DELIMITER}{data}"
    message_encoded = message.encode(FORMAT)
    msg_length = len(message_encoded)
    header = f'HEAD {msg_length}'.encode(FORMAT)
    header += b' ' * (HEADER - len(header))
    protocol_message = header + message_encoded
    return protocol_message

def update_list(client, addr, download_list, list_lock):
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
                filepath = "database\\" + filename
                sent = 0
                if file_exists(filename):
                    client.sendall(apply_protocol("SEN", "OK" + DELIMITER + filename + DELIMITER + str(os.path.getsize(filepath))))
                    with list_lock:
                        download_list.append((filename, priority, sent))
                else:
                    print(f"[ERROR] {filename} requested from {addr} does not exist!")
                    client.sendall(apply_protocol("ERR", filename))
        except Exception as e:
            print(f"Error {e}")
            continue

def process_list(client, addr, download_list, list_lock):
    while True:
        try:
            i = 0
            while i < len(download_list):
                with list_lock:
                    filename, priority_key, sent = download_list[i]

                filepath = "database\\" + filename
                done = False

                with open(filepath, 'rb') as output:
                    output.seek(sent * CHUNK_SIZE)
                    priority = PRIORITY.get(priority_key, 0)

                    for _ in range(priority):
                        chunk = output.read(CHUNK_SIZE)
                        if not chunk:
                            client.sendall(apply_protocol("SEN", "END" + DELIMITER + filename))
                            print(f"[SEND] Sent {filename} to {addr} successfully!")
                            with list_lock:
                                download_list.pop(i)
                            done = True
                            break
                        client.sendall(apply_protocol("SEF", filename))
                        client.sendall(chunk)
                        sent += 1

                if not done:
                    with list_lock:
                        download_list[i] = (filename, priority_key, sent)
                    i += 1
        except Exception as e:
            print(f"Error {e}")
            continue

def handle_client(client, addr):
    print(f"[NEW CONNECTION] A new connection is accepted from {addr}")
    file_list = load_file_list()
    client.sendall(apply_protocol("SEN", file_list))
    download_list = []
    list_lock = threading.Lock()
    try:
        list_process = threading.Thread(target=process_list, args=(client, addr, download_list, list_lock))
        list_update = threading.Thread(target=update_list, args=(client, addr, download_list, list_lock))
        list_process.start()
        list_update.start()
        list_process.join()
        list_update.join()
    except Exception as e:
        print(f"Error: {e}")
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
