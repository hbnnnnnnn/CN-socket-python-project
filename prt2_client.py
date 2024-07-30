import socket
from tqdm import tqdm
import sys
import signal
import threading
from time import sleep
import os

PORT = None
HOST = None

HEADER = 64
FORMAT = "utf-8"
CHUNK_SIZE = 1024
INPUT_FILE = "input.txt"
OUTPUT_FOLDER = "output"
DELIMITER = ' '

DOWNLOADS = []
PROCESSED_TRACKER = 0
FILE_LIST = []

shutdown_event = threading.Event()

def apply_protocol(method, message):
    message = f"{method}{DELIMITER}{message}"
    message_encoded = message.encode(FORMAT)
    message_length = len(message_encoded)

    header = ("HEAD " + str(message_length)).encode(FORMAT)
    header += b' ' * (HEADER - len(header))

    return header + message_encoded

def disconnect(sig, frame, conn):    
    shutdown_event.set()

    try:
        conn.close()
    except:
        pass

    for file in DOWNLOADS:
        file[1].close()
    
    print()
    print("  Disconnected from server.")
    print("  Program terminated.")
    sys.exit(0)

def setup_signal_handler(conn):
    signal.signal(signal.SIGINT, lambda sig, frame: disconnect(sig, frame, conn))

def get_complete_message(conn, message_length):
    data = b''
    while len(data) < message_length and not shutdown_event.is_set():
        try:
            packet = conn.recv(message_length - len(data))
            if not packet:
                return None
            data += packet
        except Exception as e:
            if not shutdown_event.is_set():
                print(f"Error receiving message: {e}")
            return None
    return data

def get_file_list(conn):
    try:
        header = get_complete_message(conn, HEADER).decode(FORMAT)

        if header is None:
            return None
        
        message_length = int(header[5:])
        message = get_complete_message(conn, message_length).decode(FORMAT)

        if message is None:
            return None
        
        method, file_list = message.split(DELIMITER, 1)

        if method == "SEN":
            return file_list
        return None
    except Exception as e:
        if not shutdown_event.is_set():
            print(f"Error getting file list: {e}")
        return None

def request_file(conn, file_name, priority):
    request = f"{file_name}{DELIMITER}{priority}"
    conn.sendall(apply_protocol("GET", request))

def respond_to_server(conn):
    global DOWNLOADS
    try:
        while not shutdown_event.is_set():
            header = get_complete_message(conn, HEADER).decode(FORMAT)
            if header is None:
                break

            if header.startswith("HEAD"):
                message_length = int(header[5:])
                message = get_complete_message(conn, message_length)
                method = message[:3].decode(FORMAT)

                if method == "SEN":
                    message = message.decode(FORMAT)
                    tag = message.split()[1]

                    if tag == "OK":
                        file_name, file_size = message.split()[2:]
                        file_size = int(file_size)
                        
                        progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc= ' ' * 2 + file_name, colour='green')
                        completed = False

                        file_path = os.path.join(OUTPUT_FOLDER, f"received_{file_name}")

                        with open(file_path, 'wb') as file:
                            pass

                        for file in DOWNLOADS:
                            if file_name == file[0]:
                                file[1] = progress_bar
                                file[2] = completed
                                break
                    
                    elif tag == "END":
                        file_name = message.split()[2]

                        for i, file in enumerate(DOWNLOADS):
                            if file[0] == file_name:
                                for item in DOWNLOADS:
                                        item[1].clear()
                                
                                file[1].close()
                               
                                j = i + 1
                                for item in DOWNLOADS[j:]:
                                    item[1].pos -= 1

                                DOWNLOADS[i][2] = True
                                break
                elif method == "SEF":
                    data = message[-CHUNK_SIZE:]
                    metadata = message[4:-CHUNK_SIZE].decode(FORMAT).split(DELIMITER)
                    
                    file_name = metadata[0]
                    data_size = int(metadata[1])

                    data = data[:data_size]

                    file_path = os.path.join(OUTPUT_FOLDER, f"received_{file_name}")

                    with open(file_path, 'ab') as file:
                        file.write(data)

                    for file in DOWNLOADS:
                        if file[0] == file_name:
                            if not shutdown_event.is_set():
                                file[1].update(len(data))
                                break      
                elif method == "ERR":
                    print(f"  [ERROR] <{file_name}> does not exist on the server.")
    except Exception as e:
        if not shutdown_event.is_set():
            print(f"Error in respond_to_server: {e}")

def process_input_file(conn):
    global PROCESSED_TRACKER, FILE_LIST

    with open(INPUT_FILE, 'r') as file:
        contents = [line.rstrip() for line in file]

    if len(contents) != PROCESSED_TRACKER:
        start_downloading_from = PROCESSED_TRACKER
        for line in contents[start_downloading_from:]:
            if shutdown_event.is_set():
                break

            file_name, priority = line.split(DELIMITER, 1)
            
            if file_name in FILE_LIST and file_name not in [item[0] for item in DOWNLOADS]: 
                request_file(conn, file_name, priority)
                DOWNLOADS.append([file_name, None, None])

            elif file_name not in FILE_LIST:
                flag = False

                for file in DOWNLOADS:
                    if file[2] == True:
                        flag = True
                        break
                        
                if flag:
                    tqdm.write(f"\n  [ERROR] <{file_name}> does not exist on the server.\n")
                else: 
                    tqdm.write(f"  [ERROR] <{file_name}> does not exist on the server.\n")
            else:
                flag = False 

                for file in DOWNLOADS:
                    if file[2] == True:
                        flag = True
                        break
                        
                if flag:
                    tqdm.write(f"\n  [WARNING] <{file_name}> has already been requested!\n")
                else: 
                    tqdm.write(f"  [WARNING] <{file_name}> has already been requested!\n")
                
            PROCESSED_TRACKER += 1

def update_input_file(conn):
    while not shutdown_event.is_set():
        process_input_file(conn)
        for _ in range(20):  
            if shutdown_event.is_set():
                break
            sleep(0.1)

def initiate_connection():
    global PROCESSED_TRACKER, FILE_LIST

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

        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)

        server_handler = threading.Thread(target=respond_to_server, args=[client])
        server_handler.start()

        input_file_handler = threading.Thread(target=update_input_file, args=[client])
        input_file_handler.start()

        try:
            while not shutdown_event.is_set():
                sleep(0.1)
        except (KeyboardInterrupt):
            pass

if __name__ == "__main__":
    HOST = input("Enter the host IP address: ")
    PORT = input("Enter the port number: ")
    HOST = HOST.replace(" ", "")
    PORT = int(PORT.replace(" ", ""))
    print("Connecting to server...")
    initiate_connection()
