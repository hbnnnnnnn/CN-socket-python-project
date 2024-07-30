import socket
import os

PORT = 9999
HOST = socket.gethostbyname(socket.gethostname())

HEADER = 64
FORMAT = 'utf-8'
CHUNK_SIZE = 1024

FILE_LIST_PATH = 'file_list.txt'
DELIMITER = ' '

def load_file_list():
    with open(FILE_LIST_PATH, 'r') as file:
        return file.read()

def file_exists(filename):
    with open(FILE_LIST_PATH, 'r') as file:
        file_list = [line.split()[0] for line in file.read().splitlines()]
    return filename in file_list and os.path.exists(FILE_LIST_PATH)

def apply_protocol(method, data, chunk = b''):
    if not chunk:
        message = f"{method}{DELIMITER}{data}"
        message_encoded = message.encode(FORMAT)
        
        msg_length = len(message_encoded)
    else:
        message = f"{method}{DELIMITER}{data}{DELIMITER}"

        if len(chunk) < 1024:
            chunk += b'\x00' * (1024 - len(chunk))

        message_encoded = message.encode(FORMAT) + chunk
        msg_length = len(message_encoded)
        
    header = f'HEAD {msg_length}'.encode(FORMAT)
    header += b' ' * (HEADER - len(header))

    protocol_message = header + message_encoded

    return protocol_message


def handle_client(client, addr):
    print(f"[NEW CONNECTION] A new connection is accepted from {addr}")
    
    file_list = load_file_list()
    client.sendall(apply_protocol("SEN", file_list))
    while True:
        try:
            str_header = client.recv(HEADER).decode(FORMAT)
            if not str_header:
                break
            msg_length = int(str_header.split()[1])
            message = client.recv(msg_length).decode(FORMAT)
            msg_parts = message.split()
            method = msg_parts[0]

            if len(msg_parts) == 2:
                filename = msg_parts[1]
                if method == "GET":
                    if file_exists(filename):
                        print(f"[SEND] Sending {filename} to {addr}...")
                        client.send(apply_protocol("SEN", "OK" + DELIMITER + str(os.path.getsize(filename))))
                        
                        with open(filename, 'rb') as output:
                            chunk = output.read(CHUNK_SIZE)

                            while chunk:
                                data_size = len(chunk)
                                
                                message = apply_protocol("CHK", f"{data_size}", chunk)
                                client.sendall(message)

                                chunk = output.read(CHUNK_SIZE)

                        print(f"[SEND] Sent {filename} to {addr} successfully!")
                    else:
                        client.sendall(apply_protocol("ERR", filename))
                        print(f"[ERROR] {filename} requested from {addr} does not exist!")
                        
        #wrong format
        except Exception as e:
            break
    print(f"[DISCONNECTED] {addr} has disconnected!")
    client.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen(1)
        print(f"Server is listening on {HOST}:{PORT}")
        try:
            while True:
                client, addr = server.accept()
                handle_client(client, addr)
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    print("Server is starting....")
    start_server()
