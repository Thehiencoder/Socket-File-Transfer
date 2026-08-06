import socket
import os
import time
import sys

# Add root path to import from config and common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import PORT, HOST, CHUNK_SIZE, MAX_CLIENTS
from common.logger import setup_logger
from src.phase1.protocol import recv_command, send_command, send_file_chunk, recv_file_chunk
from common.checksum import calculate_checksum
from common.file_manager import get_safe_path, write_file_chunk, get_file_size, read_file_chunk

logger = setup_logger("Phase1_Server", "server_phase1.log")
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "default")
os.makedirs(STORAGE_DIR, exist_ok=True)

def handle_client(conn, addr):
    """Handle incoming client connection and process file commands sequentially."""
    logger.info(f"Connected to {addr}")
    try:
        while True:
            cmd = recv_command(conn)
            if not cmd:
                break
            
            logger.info(f"[{addr}] Received cmd: {cmd}")
            start_time = time.time()
            
            parts = cmd.split(maxsplit=1)
            op = parts[0].upper()
            
            if op == "LIST":
                files = os.listdir(STORAGE_DIR) if os.path.exists(STORAGE_DIR) else []
                # Filter to include only files, excluding directories
                files = [f for f in files if os.path.isfile(os.path.join(STORAGE_DIR, f))]
                send_command(conn, "ACK " + ",".join(files))
                
            elif op == "UPLOAD":
                if len(parts) < 2:
                    send_command(conn, "ERROR Missing filename")
                    continue
                filename = parts[1]
                if not filename:
                    send_command(conn, "ERROR Invalid filename")
                    continue
                    
                filepath = get_safe_path(STORAGE_DIR, filename)
                send_command(conn, "ACK READY")
                
                # Receive expected file size
                file_info = recv_command(conn)
                if not file_info.startswith("SIZE "):
                    continue
                expected_size = int(file_info.split()[1])
                
                received = 0
                while received < expected_size:
                    chunk = recv_file_chunk(conn)
                    if not chunk:
                        break
                    write_file_chunk(filepath, received, chunk)
                    received += len(chunk)
                
                # Receive checksum from client and compare
                client_checksum_cmd = recv_command(conn)
                if client_checksum_cmd.startswith("CHECKSUM"):
                    client_checksum = client_checksum_cmd.split(" ")[1]
                    server_checksum = calculate_checksum(filepath, CHUNK_SIZE)
                    
                    elapsed = time.time() - start_time
                    speed = (received / 1024) / elapsed if elapsed > 0 else 0
                    logger.info(f"[{addr}] UPLOAD {filename} completed in {elapsed:.2f}s ({speed:.2f} KB/s)")
                    
                    if client_checksum == server_checksum:
                        send_command(conn, "ACK UPLOAD_SUCCESS")
                    else:
                        send_command(conn, "ERROR CHECKSUM_MISMATCH")
                
            elif op == "DOWNLOAD":
                if len(parts) < 2:
                    send_command(conn, "ERROR Missing filename")
                    continue
                filename = parts[1]
                filepath = get_safe_path(STORAGE_DIR, filename)
                
                if not os.path.exists(filepath):
                    send_command(conn, "ERROR FILE_NOT_FOUND")
                    continue
                    
                file_size = get_file_size(filepath)
                send_command(conn, f"ACK SIZE {file_size}")
                
                sent = 0
                while sent < file_size:
                    chunk = read_file_chunk(filepath, sent, CHUNK_SIZE)
                    if not chunk:
                        break
                    send_file_chunk(conn, chunk)
                    sent += len(chunk)
                    
                server_checksum = calculate_checksum(filepath, CHUNK_SIZE)
                send_command(conn, f"CHECKSUM {server_checksum}")
                
                elapsed = time.time() - start_time
                speed = (sent / 1024) / elapsed if elapsed > 0 else 0
                logger.info(f"[{addr}] DOWNLOAD {filename} completed in {elapsed:.2f}s ({speed:.2f} KB/s)")
            else:
                send_command(conn, "ERROR INVALID_COMMAND")

    except Exception as e:
        logger.error(f"[{addr}] Error: {e}")
    finally:
        conn.close()
        logger.info(f"Disconnected from {addr}")

def main():
    """Initialize server socket and run sequential connection accept loop."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(MAX_CLIENTS)
    logger.info(f"Phase 1 Server started on {HOST}:{PORT}")
    
    try:
        while True:
            conn, addr = server.accept()
            # Per R1.1 requirement, accept loop processes each client sequentially
            handle_client(conn, addr)
    except KeyboardInterrupt:
        logger.info("Server shutting down by user.")
    except Exception as e:
        logger.error(f"Server crashed: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    main()