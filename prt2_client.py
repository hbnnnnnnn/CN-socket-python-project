import socket
from tqdm import tqdm
import re
import sys
import signal
import threading

HEADER = 64
FORMAT = "utf-8"
CHUNK_SIZE = 1024
PORT = 1603
HOST = socket.gethostbyname(socket.gethostname())
INPUT_FILE = "input.txt"
DELIMITER = ' '
DOWNLOADED_TRACKER = 0

PRIORITY = {
    "NORMAL": 1,
    "HIGH": 4,
    "CRITICAL": 10
}

DOWNLOADS = []

def apply_protocol(method, message):
    message = f"{method}{DELIMITER}{message}"
    message_encoded = message.encode(FORMAT)
    message_length = len(message_encoded)

    header = ("HEAD " + str(message_length)).encode(FORMAT)
    header += b' ' * (HEADER - len(header))

    return header + message_encoded

def disconnect(sig, frame, conn):
    try:
        conn.close()
    except:
        pass
    print("Disconnect successfully!")
    sys.exit(0)

def setup_signal_handler(conn):
    signal.signal(signal.SIGINT, lambda sig, frame: disconnect(sig, frame, conn))

def get_complete_message(conn, message_length):
    data = b''
    while len(data) < message_length:
        packet = conn.recv(message_length - len(data))
        if not packet:
            return None
        data += packet
    return data

def get_file_list(conn):
    try: 
        header = conn.recv(HEADER).decode(FORMAT)
        message_length = int(header[5:])
        message = get_complete_message(conn, message_length).decode(FORMAT)
        method, file_list = message.split(' ', 1)

        if method == "SEN":
            return file_list
        return None
    except Exception as e:
        print(f"Error getting file list: {e}")
        return None

def request_file(conn, file_name, priority):
    request = f"{file_name}{DELIMITER}{priority}"
    conn.sendall(apply_protocol("GET", request))

def respond_to_server(conn):
    while True:
        try:
            header = conn.recv(HEADER).decode(FORMAT)
            if header.startswith("HEAD"):
                message_length = int(header[5:])
                message = get_complete_message(conn, message_length).decode(FORMAT)
                method = message.split()[0]

                if method == "SEN":
                    tag = message.split()[1]

                    if tag == "OK":
                        file_name, file_size = message.split()[2:]
                        file_size = int(file_size)

                        progress = tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc=file_name)

                        DOWNLOADS.append([file_name, progress])
                    
                    if tag == "END":
                        file_name = message.split()[2]

                        for file in DOWNLOADS:
                            if file[0] == file_name:
                                file[1].close()
                                DOWNLOADS.remove(file)
                                break

                elif method == "SEF":
                    file_name = message.split()[1]
                    data = conn.recv(CHUNK_SIZE)

                    with open(f"receive_{file_name}", 'ab') as file:
                        file.write(data)

                    for file in DOWNLOADS:
                        if file[0] == file_name:
                            file[1].update(len(data))
                            break

                elif method == "ERR":
                    file_name = message.split([1])
                    print(f"Error: File '{file_name}' does not exist on the server.")
                    
        except:
            continue
        
def update_input_file(conn):
    global DOWNLOADED_TRACKER

    with open(INPUT_FILE, 'r') as file:
        contents = [line.rstrip() for line in file]

    if len(contents) != DOWNLOADED_TRACKER:
        start_downloading_from = DOWNLOADED_TRACKER
        for line in contents[start_downloading_from:]:
            file_name, priority = line.split(DELIMITER, 1)
            print(file_name)
            print(priority)
            request_file(conn, file_name, priority)
            DOWNLOADED_TRACKER += 1

    threading.Timer(2, update_input_file, [conn]).start()

def initiate_connection():
    global DOWNLOADED_TRACKER

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        setup_signal_handler(client)

        file_list = get_file_list(client)

        if file_list:
            print("Available files on server:")
            print(file_list + '\n')
            file_sizes = dict(item.split(DELIMITER) for item in file_list.split('\n'))
        else:
            print("Failed to retrieve file list.")
            return

        server_handller = threading.Thread(target=respond_to_server, args=(client,))
        server_handller.start()

        update_input_file(client)
    
if __name__ == "__main__":
    print("Connecting to server...")
    initiate_connection()
