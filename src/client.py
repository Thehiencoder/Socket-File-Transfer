import asyncio
import os
import sys
import struct
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PORT, HOST, CHUNK_SIZE
from common.checksum import calculate_checksum
from common.file_manager import get_file_size, read_file_chunk, write_file_chunk
from src.protocol import (
    Opcode, pack_upload_req, pack_ack_offset,
    send_binary_packet_async, recv_binary_packet_async,
    send_text_payload_async
)

class AsyncClient:
    """Asynchronous socket client supporting authentication, list, resumable upload/download, and checksum verification."""
    def __init__(self, username: str):
        self.username = username
        self.user_id = 0
        self.reader = None
        self.writer = None

    async def connect(self):
        """Establish connection with the server and perform login handshake."""
        try:
            self.reader, self.writer = await asyncio.open_connection(HOST, PORT)
            # Send login command
            await send_text_payload_async(self.writer, Opcode.LOGIN, 0, self.username)
            opcode, self.user_id, payload = await recv_binary_packet_async(self.reader)
            
            if opcode == Opcode.ERROR:
                print(f"Connection rejected: {payload.decode('utf-8')}")
                return False
                
            if opcode == Opcode.ACK and payload.decode('utf-8') == "LOGIN_OK":
                print(f"Connected to server as '{self.username}'")
                return True
            return False
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Close writer stream to disconnect from server."""
        if self.writer:
            self.writer.close()

    async def cmd_list(self):
        """Request and print list of files stored on the server for this user."""
        await send_binary_packet_async(self.writer, Opcode.LIST_REQ, self.user_id, b"")
        opcode, _, payload = await recv_binary_packet_async(self.reader)
        if opcode == Opcode.LIST_RESP:
            files_str = payload.decode('utf-8')
            if files_str:
                print("Files on server:")
                for f in files_str.split(","):
                    print(f" - {f}")
            else:
                print("Server is empty.")
        elif opcode == Opcode.ERROR:
            print("Server error:", payload.decode('utf-8'))

    async def cmd_upload(self, filepath: str):
        """Upload a file to the server with resume capability and checksum verification."""
        if not os.path.exists(filepath):
            print(f"File {filepath} not found.")
            return

        filename = os.path.basename(filepath)
        file_size = get_file_size(filepath)
        
        # Send UPLOAD_REQ
        req_payload = pack_upload_req(file_size, filename)
        await send_binary_packet_async(self.writer, Opcode.UPLOAD_REQ, self.user_id, req_payload)
        
        # Receive ACK with offset (for Resume)
        opcode, _, ack_payload = await recv_binary_packet_async(self.reader)
        if opcode == Opcode.ERROR:
            print("Server error:", ack_payload.decode('utf-8'))
            return
        if opcode != Opcode.ACK:
            print("Unexpected response from server.")
            return
            
        offset = struct.unpack("!Q", ack_payload)[0]
        
        if offset > 0:
            print(f"Resuming upload from {offset}/{file_size} bytes...")
        else:
            print(f"Uploading {filename} ({file_size} bytes)...")
            
        sent = offset
        
        # Tqdm Progress Bar
        with tqdm(total=file_size, initial=sent, unit='B', unit_scale=True, desc=filename) as pbar:
            while sent < file_size:
                # Read file chunk asynchronously using executor
                chunk = await asyncio.get_running_loop().run_in_executor(
                    None, read_file_chunk, filepath, sent, CHUNK_SIZE
                )
                if not chunk:
                    break
                    
                await send_binary_packet_async(self.writer, Opcode.FILE_CHUNK, self.user_id, chunk)
                sent += len(chunk)
                pbar.update(len(chunk))
                
        # Calculate & send checksum
        print("Calculating checksum...")
        client_checksum = await asyncio.get_running_loop().run_in_executor(
            None, calculate_checksum, filepath, CHUNK_SIZE
        )
        await send_text_payload_async(self.writer, Opcode.CHECKSUM_REQ, self.user_id, client_checksum)
        
        # Verify response
        opcode, _, payload = await recv_binary_packet_async(self.reader)
        if opcode == Opcode.ACK and payload.decode('utf-8') == "CHECKSUM_MATCH":
            print("Upload successful! Checksum verified.")
        else:
            print(f"Error: {payload.decode('utf-8')}")

    async def cmd_download(self, filename: str, save_dir: str = "downloads"):
        """Download a file from the server with resume capability and checksum verification."""
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        
        # Check if local file exists to send offset for resume
        offset = get_file_size(filepath) if os.path.exists(filepath) else 0
        
        # Send DOWNLOAD_REQ
        req_payload = struct.pack("!Q", offset) + filename.encode('utf-8')
        await send_binary_packet_async(self.writer, Opcode.DOWNLOAD_REQ, self.user_id, req_payload)
        
        # Receive ACK containing total file size
        opcode, _, ack_payload = await recv_binary_packet_async(self.reader)
        if opcode == Opcode.ERROR:
            print("Server error:", ack_payload.decode('utf-8'))
            return
        if opcode != Opcode.ACK:
            print("Unexpected response from server.")
            return
            
        file_size = struct.unpack("!Q", ack_payload)[0]
        
        if offset > 0 and offset < file_size:
            print(f"Resuming download from {offset}/{file_size} bytes...")
        elif offset >= file_size and file_size > 0:
            print("File is already fully downloaded.")
            # Server might still send checksum, client can self-check
            return
        else:
            print(f"Downloading {filename} ({file_size} bytes)...")
            
        received = offset
        
        # Tqdm Progress Bar
        with tqdm(total=file_size, initial=received, unit='B', unit_scale=True, desc=filename) as pbar:
            while received < file_size:
                chunk_op, _, chunk_payload = await recv_binary_packet_async(self.reader)
                if chunk_op != Opcode.FILE_CHUNK:
                    break
                    
                await asyncio.get_running_loop().run_in_executor(
                    None, write_file_chunk, filepath, received, chunk_payload
                )
                received += len(chunk_payload)
                pbar.update(len(chunk_payload))
                
        # Receive checksum from server
        opcode, _, payload = await recv_binary_packet_async(self.reader)
        if opcode == Opcode.CHECKSUM_RESP:
            server_checksum = payload.decode('utf-8')
            print("Calculating local checksum...")
            local_checksum = await asyncio.get_running_loop().run_in_executor(
                None, calculate_checksum, filepath, CHUNK_SIZE
            )
            
            if local_checksum == server_checksum:
                print("Download successful! Checksum verified.")
            else:
                print("WARNING: Checksum mismatch!")
        else:
            print("Did not receive checksum from server.")

async def interactive_shell(client: AsyncClient):
    """Run an interactive CLI command shell for the client."""
    loop = asyncio.get_running_loop()
    while True:
        try:
            # Run blocking input() in a separate thread executor to avoid blocking the event loop
            cmd = await loop.run_in_executor(None, input, "FTP> ")
            cmd = cmd.strip()
            if not cmd:
                continue
                
            parts = cmd.split(maxsplit=1)
            op = parts[0].upper()
            
            if op == "QUIT" or op == "EXIT":
                break
            elif op == "LIST":
                await client.cmd_list()
            elif op == "UPLOAD":
                if len(parts) < 2:
                    print("Usage: UPLOAD <filepath>")
                else:
                    await client.cmd_upload(parts[1])
            elif op == "DOWNLOAD":
                if len(parts) < 2:
                    print("Usage: DOWNLOAD <filename>")
                else:
                    await client.cmd_download(parts[1])
            else:
                print("Unknown command. Supported: LIST, UPLOAD <file>, DOWNLOAD <file>, QUIT")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error executing command: {e}")

async def main():
    """Main entry point to initialize client connection and interactive shell."""
    username = input("Enter username: ").strip()
    if not username:
        username = "guest"
        
    client = AsyncClient(username)
    if await client.connect():
        await interactive_shell(client)
        client.disconnect()

if __name__ == "__main__":
    # Workaround for "Event loop is closed" RuntimeError on Windows (Python 3.8+)
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())