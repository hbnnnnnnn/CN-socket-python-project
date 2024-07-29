import socket
from tqdm import tqdm
import sys
import signal
import os

PORT = 1603
HOST = socket.gethostbyname(socket.gethostname())

HEADER = 64
FORMAT = "utf-8"
CHUNKS_SIZE = 1024
INPUT_FILE = "input1.txt"
DELIMITER = ' '

DOWNLOADS = []
PROCESSED_TRACKER = 0
FILE_LIST = []
PROGRESS_BAR = None
IS_CLOSED = True

def apply_protocol(method, message):
    message = f"{method}{DELIMITER}{message}"
    message_encoded = message.encode(FORMAT)
    message_length = len(message_encoded)

    header = ("HEAD " + str(message_length)).encode(FORMAT)
    header += b' ' * (HEADER - len(header))

    return header + message_encoded

def disconnect(sig, frame, conn):
    global IS_CLOSED
    global PROGRESS_BAR

    disconnect_msg = apply_protocol("DIS", "")
    conn.sendall(disconnect_msg)
    
    try:
        conn.close()
    except:
        pass

    if not IS_CLOSED:
        PROGRESS_BAR.close()
        print()

    print("  Disconnected from server.")
    print("  Program terminated.")
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
        print(f"[ERROR] Unable to get file list from server: {e}")
        return None

def request_file(conn, file_name):
    global PROGRESS_BAR
    global IS_CLOSED

    try:
        request_message = apply_protocol("GET", file_name)
        conn.sendall(request_message)

        header = conn.recv(HEADER).decode(FORMAT)
        if header.startswith("HEAD"):
            message_length = int(header[5:])
            message = get_complete_message(conn, message_length).decode(FORMAT)
            method, status, file_size = message.split(' ', 2)
            file_size = int(file_size)

            if method == "SEN" and status == "OK":
                PROGRESS_BAR = tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024, colour='green', desc= 2 * ' ' + file_name)
                IS_CLOSED = False

                output_folder = "output"

                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)

                file_path = os.path.join(output_folder, f"receive_{file_name}")
                              
                with open(file_path, 'wb') as file:
                    data_received = 0

                    while True:
                        try:
                            chunk = conn.recv(CHUNKS_SIZE)
                            data_received += len(chunk)

                            if data_received == file_size:
                                break

                            file.write(chunk)
                            PROGRESS_BAR.update(len(chunk))
                        except:
                            PROGRESS_BAR.close()
                            IS_CLOSED = True

                PROGRESS_BAR.close() 
                IS_CLOSED = True

                print()
            elif method == "ERR":
                print(f"  [ERROR] <{file_name}> does not exist on the server.")
    except Exception as e:
        print(f"[ERROR] Error requesting file: {e}")

def initiate_connection():
    global PROCESSED_TRACKER
    global FILE_LIST

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        print(f"Connected to server at {(HOST, PORT)}\n")

        setup_signal_handler(client)

        file_list = get_file_list(client)

        if file_list:
            print("Available files on server:\n")
            for line in file_list.splitlines():
                file_name = line.split()[0]
                file_size = line.split()[1]
                print('  - ' + file_name + (16 - len(file_name)) * " " + ": " + file_size)

            print()

            FILE_LIST = [file.split()[0] for file in file_list.splitlines()]
        else:
            print("Failed to retrieve file list.")
            return
        
        print("Home:\n")

        while True:
            with open(INPUT_FILE, 'r') as file:
                contents = [line.rstrip() for line in file]

            start_downloading_from = PROCESSED_TRACKER
            for item in contents[start_downloading_from:]:
                file_name = item

                if file_name in FILE_LIST and file_name not in DOWNLOADS: 
                    request_file(client, file_name)
                    DOWNLOADS.append(file_name)

                elif file_name not in FILE_LIST:
                    print(f"  [ERROR] <{file_name}> does not exist on the server.\n")
                else:
                    print(f"  [WARNING] <{file_name}> has already been requested!\n")
                    
                PROCESSED_TRACKER += 1

if __name__ == "__main__":
    print("Connecting to server...")
    initiate_connection()
