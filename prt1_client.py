import socket
from tqdm import tqdm
import re
import sys
import signal

HEADER = 64
FORMAT = 'utf-8'
CHUNKS_SIZE = 1024
PORT = 1603
HOST = socket.gethostbyname(socket.gethostname())
INPUT_FILE = "input.txt"
DELIMITER = ' '
DOWNLOADED_TRACKER = 0

SIZE = {
    "B": 1,
    "KB": 1024,
    "MB": 1024 * 1024,
    "GB": 1024 * 1024 * 1024
}

def apply_protocol(method, message):
    message = f"{method}{DELIMITER}{message}"
    message_encoded = message.encode(FORMAT)
    message_length = len(message_encoded)

    header = ("HEAD " + str(message_length)).encode(FORMAT)
    header += b' ' * (HEADER - len(header))

    return header + message_encoded

def disconnect(sig, frame, conn):
    message = apply_protocol("END", "")
    conn.sendall(message)
    conn.close()
    sys.exit(0)

def setup_signal_handler(conn):
    signal.signal(signal.SIGINT, lambda sig, frame: disconnect(sig, frame, conn))
    
def split_number_unit(s):
    match = re.match(r"(\d+)([a-zA-Z]+)", s)
    if match:
        number = int(match.groups()[0])
        unit = match.groups()[1]
        return number * SIZE.get(unit, 1)
    return None

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

def request_file(conn, file_name, file_size):
    try:
        request_message = apply_protocol("GET", file_name)
        conn.sendall(request_message)

        header = conn.recv(HEADER).decode(FORMAT)
        if header.startswith("HEAD"):
            message_length = int(header[5:])
            message = get_complete_message(conn, message_length).decode(FORMAT)
            method, status = message.split(' ', 1)

            if method == "SEN" and status == "OK":
                progress = tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc=file_name)

                with open(f"receive_{file_name}", 'wb') as file:
                    data_received = 0
                    while True:
                        chunk = conn.recv(CHUNKS_SIZE)
                        data_received += len(chunk)
                        if data_received == file_size:
                            break
                        file.write(chunk)
                        progress.update(len(chunk))
                progress.close()

                print(f"File '{file_name}' received successfully!")
                return True
            elif method == "ERR":
                print(f"Error: File '{file_name}' does not exist on the server.")
                return False
    except Exception as e:
        print(f"Error requesting file: {e}")
        return False

def initiate_connection():
    global DOWNLOADED_TRACKER
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        setup_signal_handler(client)
        
        file_list = get_file_list(client)

        if file_list:
            print("File list received:")
            print(file_list)
            file_sizes = dict(item.split(' ') for item in file_list.split('\n'))
        else:
            print("Failed to retrieve file list.")
            return

        while True:
            with open(INPUT_FILE, 'r') as file:
                contents = [line.rstrip() for line in file]

            start_downloading_from = DOWNLOADED_TRACKER
            for line in contents[start_downloading_from:]:
                file_name = line
                file_size = file_sizes.get(file_name)
                file_size = split_number_unit(file_size)

                successful = request_file(client, file_name, file_size)
                
                if successful:
                    DOWNLOADED_TRACKER += 1

if __name__ == "__main__":
    print("Connecting to server...")
    initiate_connection()
