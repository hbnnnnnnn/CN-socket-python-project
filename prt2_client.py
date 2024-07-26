import socket
from tqdm import tqdm
import sys
import signal
import threading
import time
from time import sleep
import os

PORT = 1603
HOST = socket.gethostbyname(socket.gethostname())

HEADER = 64
FORMAT = "utf-8"
CHUNK_SIZE = 1024
INPUT_FILE = "input.txt"
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

def disconnect(sig, frame):    
    shutdown_event.set()
    for file in DOWNLOADS:
        file[1].close()
    
    # for i in range(len(DOWNLOADS)):
    #     sys.stdout.write('\x1b[1A')  # Move cursor up one line
    #     sys.stdout.write('\x1b[2K')
    #     sys.stdout.flush()
    # os.system('cls')
    print()
    print("Program terminated.")
    sys.exit(0)

def setup_signal_handler():
    signal.signal(signal.SIGINT, disconnect)

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
        method, file_list = message.split(' ', 1)

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
                        # + ' ' * 3
                        bar_format = '{l_bar}{bar}{r_bar}' 
                        progress_bar = tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc= ' ' * 2 + file_name, colour='green', bar_format=bar_format)
                        completed = False
                        for file in DOWNLOADS:
                            if file_name == file[0]:
                                file[1] = progress_bar
                                file[2] = completed
                    
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
                    data = message[-1024:]
                    data = data.rstrip(b'\x00')

                    message = message[:-1024]
                    message = message.decode(FORMAT)

                    file_name = message.split()[1]
                    
                    output_folder = "output"

                    if not os.path.exists(output_folder):
                        os.makedirs(output_folder)

                    file_path = os.path.join(output_folder, f"receive_{file_name}")

                    with open(file_path, 'ab') as file:
                        file.write(data)

                    for file in DOWNLOADS:
                        if file[0] == file_name:
                            if not shutdown_event.is_set():
                                file[1].update(len(data))
                                break

                elif method == "ERR":
                    message = message.decode(FORMAT)
                    file_name = message.split()[1]

                    flag = False

                    for file in DOWNLOADS:
                        if file[2] == True:
                            flag = True
                            break
                            
                    if flag:
                        tqdm.write(f"\n  [ERROR] <{file_name}> does not exist on the server.\n")
                    else: 
                        tqdm.write(f"  [ERROR] <{file_name}> does not exist on the server.\n")
                    
    except Exception as e:
        if not shutdown_event.is_set():
            # print(f"Error in respond_to_server: {e}")
            pass

def process_input_file(conn):
    global PROCESSED_TRACKER
    global FILE_LIST

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
            time.sleep(0.1)

def initiate_connection():
    global PROCESSED_TRACKER
    global FILE_LIST

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        print(f"Connected to server at {(HOST, PORT)}\n")

        setup_signal_handler()

        file_list = get_file_list(client)

        if file_list:
            print("Available files on server:\n")
            for line in file_list.splitlines():
                print('  - ' + line)

            print()
            
            FILE_LIST = [file.split()[0] for file in file_list.splitlines()]
        else:
            print("Failed to retrieve file list.")
            return

        print("Home:\n")
        server_handler = threading.Thread(target=respond_to_server, args=[client])
        server_handler.start()

        input_file_handler = threading.Thread(target=update_input_file, args=[client])
        input_file_handler.start()

        try:
            while not shutdown_event.is_set():
                time.sleep(0.1)  # Sleep to reduce CPU usage
        except (KeyboardInterrupt, SystemExit):
            shutdown_event.set()
        
        input_file_handler.join()
        server_handler.join()

        client.close()
        print("DISCONNECTED")

if __name__ == "__main__":
    print("Connecting to server...")
    initiate_connection()
