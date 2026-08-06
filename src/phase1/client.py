import socket
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import PORT, HOST, CHUNK_SIZE
from src.phase1.protocol import send_command, recv_command, send_file_chunk, recv_file_chunk
from common.checksum import calculate_checksum
from common.file_manager import get_file_size, read_file_chunk, write_file_chunk

def cmd_list(sock):
    send_command(sock, "LIST")
    response = recv_command(sock)
    if response.startswith("ACK"):
        files = response[4:]
        if files:
            print("Files on server:")
            for f in files.split(","):
                print(f" - {f}")
        else:
            print("Server is empty.")
    else:
        print("Error:", response)

def cmd_upload(sock, filepath):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found.")
        return
        
    filename = os.path.basename(filepath)
    send_command(sock, f"UPLOAD {filename}")
    response = recv_command(sock)
    
    if not response.startswith("ACK READY"):
        print("Server error:", response)
        return
        
    file_size = get_file_size(filepath)
    send_command(sock, f"SIZE {file_size}")
    
    sent = 0
    print(f"Uploading {filename} ({file_size} bytes)...")
    while sent < file_size:
        chunk = read_file_chunk(filepath, sent, CHUNK_SIZE)
        if not chunk:
            break
        send_file_chunk(sock, chunk)
        sent += len(chunk)
        
    client_checksum = calculate_checksum(filepath, CHUNK_SIZE)
    send_command(sock, f"CHECKSUM {client_checksum}")
    
    final_response = recv_command(sock)
    print("Server:", final_response)

def cmd_download(sock, filename, save_dir="downloads"):
    send_command(sock, f"DOWNLOAD {filename}")
    response = recv_command(sock)
    
    if not response.startswith("ACK SIZE"):
        print("Server error:", response)
        return
        
    file_size = int(response.split()[2])
    filepath = os.path.join(save_dir, filename)
    os.makedirs(save_dir, exist_ok=True)
    
    received = 0
    print(f"Downloading {filename} ({file_size} bytes)...")
    while received < file_size:
        chunk = recv_file_chunk(sock)
        if not chunk:
            break
        write_file_chunk(filepath, received, chunk)
        received += len(chunk)
        
    checksum_response = recv_command(sock)
    if checksum_response.startswith("CHECKSUM"):
        server_checksum = checksum_response.split()[1]
        client_checksum = calculate_checksum(filepath, CHUNK_SIZE)
        if server_checksum == client_checksum:
            print("Download successful! Checksum verified.")
        else:
            print("WARNING: Checksum mismatch!")
    else:
        print("Did not receive checksum from server.")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        print(f"Connected to {HOST}:{PORT}")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        while True:
            cmd = input("FTP> ").strip()
            if not cmd:
                continue
                
            parts = cmd.split()
            op = parts[0].upper()
            
            if op == "QUIT" or op == "EXIT":
                break
            elif op == "LIST":
                cmd_list(sock)
            elif op == "UPLOAD":
                if len(parts) < 2:
                    print("Usage: UPLOAD <filepath>")
                else:
                    cmd_upload(sock, parts[1])
            elif op == "DOWNLOAD":
                if len(parts) < 2:
                    print("Usage: DOWNLOAD <filename>")
                else:
                    cmd_download(sock, parts[1], "downloads")
            else:
                print("Unknown command. Supported: LIST, UPLOAD <file>, DOWNLOAD <file>, QUIT")
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()
        print("Connection closed.")

if __name__ == "__main__":
    main()
