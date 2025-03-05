# File Transfer Application
A client-server file transfer CLI application, which is a project of Computer Networking course, implemented in Python.

## Part I:
- Develop a client-server application allowing multiple clients to download files from a server sequentially.

### Server:
- Use a text or JSON file to list available files with their sizes.

### Client:
- Connect to the server and display the list of files.
- Use `input.txt` file to record files to be downloaded.
- Download files sequentially and display download progress.
- Close connection and terminate program on `Ctrl + C`.

## Part II:
- Enhance the client-server application to support simultaneous client connections with priority-based file downloads.

### Server:
- Use a text or JSON file to list available files with their sizes.

### Client:
- Connect to the server and display the list of files.
- Use `input.txt` file to record files to be downloaded with priorities (CRITICAL, HIGH, NORMAL).
- Scan `input.txt` every 2 seconds for new file entries and priorities.
- Download files based on priorities using chunks, displaying download progress.
- Close connection and terminate program on `Ctrl + C`.
