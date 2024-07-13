# CN-socket-python-project
a client server communication project of computer networking course implemented in python

Part I:
- Develop a Client/Server application allowing multiple clients to download files from a server sequentially.

Server:
- Use a text or JSON file to list available files with their sizes.

Client:
- Connect to the server and display the list of files.
- Use an input.txt file to record files to be downloaded.
- Download files sequentially and display download progress.
- Close connection and terminate program on "Ctrl + C".

Part II:
- Enhance the Client/Server application to support simultaneous client connections with priority-based file downloads.
Server:
- Use a text or JSON file to list available files with their sizes.

Client:
- Connect to the server and display the list of files.
- Use an input.txt file to record files to be downloaded with priorities (CRITICAL, HIGH, NORMAL).
- Scan input.txt every 2 seconds for new file entries and priorities.
- Download files based on priorities using chunks, displaying download progress.
- Close connection and terminate program on "Ctrl + C".
