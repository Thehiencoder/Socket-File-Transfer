import asyncio
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PORT, HOST, CHUNK_SIZE, MAX_CLIENTS, SPEED_LIMIT_KBPS
from common.logger import setup_logger
from common.checksum import calculate_checksum
from common.file_manager import get_safe_path, write_file_chunk, get_file_size, read_file_chunk
from src.protocol import (
    Opcode, pack_ack_offset, unpack_upload_req, 
    send_text_payload, recv_text_payload,
    send_binary_packet_async, recv_binary_packet_async, send_text_payload_async
)
from src.throttler import TokenBucket
import struct

logger = setup_logger("Phase2_Server", "server_phase2.log")
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")

# Manage maximum concurrent connections
client_semaphore = asyncio.Semaphore(MAX_CLIENTS)

async def process_upload_req(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, payload: bytes, username: str, user_id: int, throttler: TokenBucket, addr):
    """Handle file upload request from client."""
    file_size, filename = unpack_upload_req(payload)
    filepath = get_safe_path(STORAGE_DIR, filename, username)
    
    # Check existing file for resume capability
    current_size = get_file_size(filepath)
    if current_size > 0 and current_size < file_size:
        # File incomplete -> Resume upload
        logger.info(f"[{addr}] Resume UPLOAD {filename} from {current_size}/{file_size}")
        ack_payload = pack_ack_offset(current_size)
        received = current_size
    else:
        # Overwrite (according to user overwrite policy)
        if current_size > 0:
            logger.info(f"[{addr}] Overwrite existing {filename}")
            # Delete old file for clean overwrite
            os.remove(filepath)
        logger.info(f"[{addr}] Start UPLOAD {filename} ({file_size} bytes)")
        ack_payload = pack_ack_offset(0)
        received = 0
        
    await send_binary_packet_async(writer, Opcode.ACK, user_id, ack_payload)
    
    start_time = time.time()
    bytes_this_session = 0
    
    # Receive file chunks sequentially
    while received < file_size:
        chunk_op, _, chunk_payload = await recv_binary_packet_async(reader)
        if chunk_op != Opcode.FILE_CHUNK:
            break
        
        # Apply rate limiting
        await throttler.consume(len(chunk_payload))
        
        # Offload blocking file write operation to thread pool to avoid blocking asyncio event loop
        await asyncio.get_running_loop().run_in_executor(
            None, write_file_chunk, filepath, received, chunk_payload
        )
        received += len(chunk_payload)
        bytes_this_session += len(chunk_payload)
        
    elapsed = time.time() - start_time
    speed = (bytes_this_session / 1024) / elapsed if elapsed > 0 else 0
    logger.info(f"[{addr}] UPLOAD {filename} completed. Session avg speed: {speed:.2f} KB/s")
    
    # Receive checksum from client and compare
    chunk_op, _, checksum_payload = await recv_binary_packet_async(reader)
    if chunk_op == Opcode.CHECKSUM_REQ:
        client_checksum = checksum_payload.decode('utf-8')
        server_checksum = await asyncio.get_running_loop().run_in_executor(
            None, calculate_checksum, filepath, CHUNK_SIZE
        )
        if client_checksum == server_checksum:
            await send_text_payload_async(writer, Opcode.ACK, user_id, "CHECKSUM_MATCH")
        else:
            await send_text_payload_async(writer, Opcode.ERROR, user_id, "CHECKSUM_MISMATCH")


async def process_download_req(writer: asyncio.StreamWriter, payload: bytes, username: str, user_id: int, throttler: TokenBucket, addr):
    """Handle file download request from client."""
    # Payload format: [8 bytes offset] + [filename]
    offset = struct.unpack("!Q", payload[:8])[0]
    filename = payload[8:].decode('utf-8')
    filepath = get_safe_path(STORAGE_DIR, filename, username)
    
    if not os.path.exists(filepath):
        await send_text_payload_async(writer, Opcode.ERROR, user_id, "FILE_NOT_FOUND")
        return
        
    file_size = get_file_size(filepath)
    # Notify client of total file size
    await send_binary_packet_async(writer, Opcode.ACK, user_id, struct.pack("!Q", file_size))
    
    sent = offset
    logger.info(f"[{addr}] Start DOWNLOAD {filename} from {sent}/{file_size}")
    start_time = time.time()
    bytes_this_session = 0
    
    while sent < file_size:
        # Offload blocking file read
        chunk = await asyncio.get_running_loop().run_in_executor(
            None, read_file_chunk, filepath, sent, CHUNK_SIZE
        )
        if not chunk:
            break
            
        await throttler.consume(len(chunk))
        await send_binary_packet_async(writer, Opcode.FILE_CHUNK, user_id, chunk)
        
        sent += len(chunk)
        bytes_this_session += len(chunk)
        
    elapsed = time.time() - start_time
    speed = (bytes_this_session / 1024) / elapsed if elapsed > 0 else 0
    logger.info(f"[{addr}] DOWNLOAD {filename} completed. Session avg speed: {speed:.2f} KB/s")
    
    # Send checksum for client verification
    server_checksum = await asyncio.get_running_loop().run_in_executor(
        None, calculate_checksum, filepath, CHUNK_SIZE
    )
    await send_text_payload_async(writer, Opcode.CHECKSUM_RESP, user_id, server_checksum)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Main loop to process commands from a connected client."""
    addr = writer.get_extra_info('peername')
    logger.info(f"Connected to {addr}")
    
    # Initialize dedicated throttler for this client connection
    throttler = TokenBucket(SPEED_LIMIT_KBPS)
    username = "default"
    user_id = 0
    
    try:
        while True:
            opcode, recv_user_id, payload = await recv_binary_packet_async(reader)
            if opcode is None:
                break
                
            if opcode == Opcode.LOGIN:
                username = payload.decode('utf-8')
                user_id = recv_user_id
                logger.info(f"[{addr}] LOGIN success as '{username}'")
                await send_text_payload_async(writer, Opcode.ACK, user_id, "LOGIN_OK")
                
            elif opcode == Opcode.LIST_REQ:
                user_dir = os.path.join(STORAGE_DIR, username)
                files = os.listdir(user_dir) if os.path.exists(user_dir) else []
                files = [f for f in files if os.path.isfile(os.path.join(user_dir, f))]
                await send_text_payload_async(writer, Opcode.LIST_RESP, user_id, ",".join(files))
                
            elif opcode == Opcode.UPLOAD_REQ:
                await process_upload_req(reader, writer, payload, username, user_id, throttler, addr)
                    
            elif opcode == Opcode.DOWNLOAD_REQ:
                await process_download_req(writer, payload, username, user_id, throttler, addr)
                
            else:
                logger.warning(f"[{addr}] Unknown opcode {opcode}")
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"[{addr}] Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info(f"Disconnected from {addr}")

async def client_handler_wrapper(reader, writer):
    """Wrapper to enforce maximum client connection limits."""
    if client_semaphore.locked():
        logger.warning(f"Max clients ({MAX_CLIENTS}) reached. Rejecting connection.")
        await send_text_payload_async(writer, Opcode.ERROR, 0, "MAX_CLIENTS_REACHED")
        writer.close()
        await writer.wait_closed()
        return
        
    async with client_semaphore:
        await handle_client(reader, writer)

async def main():
    """Start the asynchronous socket server."""
    server = await asyncio.start_server(client_handler_wrapper, HOST, PORT)
    addr = server.sockets[0].getsockname()
    logger.info(f"Phase 2 Async Server started on {addr}")
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down.")