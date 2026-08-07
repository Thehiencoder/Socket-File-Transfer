import asyncio
import os
import sys
import time
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PORT, HOST, MAX_CLIENTS
from src.protocol import Opcode, pack_upload_req, recv_binary_packet_async
import struct

async def simulate_client(client_id: int):
    """Simulate a client connecting, uploading dummy data, and disconnecting safely or abruptly."""
    try:
        reader, writer = await asyncio.open_connection(HOST, PORT)
        username = f"bot_{client_id}"
        print(f"[Client {client_id}] Connected as {username}")
        
        # 1. Send LOGIN
        login_payload = username.encode('utf-8')
        header = struct.pack("!IHH", len(login_payload), Opcode.LOGIN, client_id)
        writer.write(header + login_payload)
        await writer.drain()
        
        # 2. Short pause to simulate real network delay
        await asyncio.sleep(random.uniform(0.1, 0.5))
            
        # 3. Send dummy UPLOAD_REQ
        file_size = random.randint(1024, 1024 * 50)  # 1KB - 50KB
        filename = f"dummy_{client_id}.bin"
        req_payload = pack_upload_req(file_size, filename)
        header = struct.pack("!IHH", len(req_payload), Opcode.UPLOAD_REQ, client_id)
        writer.write(header + req_payload)
        await writer.drain()
        
        # WAIT FOR SERVER ACK (permission granted to start uploading)
        opcode, _, ack_payload = await recv_binary_packet_async(reader)
        if opcode != Opcode.ACK:
            print(f"[Client {client_id}] Failed to receive ACK")
            return
            
        # 4. Rapidly send entire dummy file content
        chunk_data = os.urandom(file_size)
        header = struct.pack("!IHH", file_size, Opcode.FILE_CHUNK, client_id)
        writer.write(header + chunk_data)
        await writer.drain()
        print(f"[Client {client_id}] Uploaded {filename} ({file_size} bytes)")
        
        # 5. Send dummy CHECKSUM to properly finalize the upload process
        checksum_payload = b"dummy_checksum"
        header = struct.pack("!IHH", len(checksum_payload), Opcode.CHECKSUM_REQ, client_id)
        writer.write(header + checksum_payload)
        await writer.drain()
        
        # Wait for server checksum response before exiting
        opcode, _, checksum_resp = await recv_binary_packet_async(reader)
        if opcode == Opcode.ACK:
            print(f"[Client {client_id}] Server verified checksum successfully.")
        
        # 6. Disconnect safely
        writer.close()
        await writer.wait_closed()
        print(f"[Client {client_id}] Finished and disconnected safely.")
        
    except Exception as e:
        print(f"[Client {client_id}] Error: {e}")

async def main():
    NUM_CLIENTS = MAX_CLIENTS
    print(f"Starting stress test simulation with {NUM_CLIENTS} concurrent clients...")
    start_time = time.time()
    
    # Create and execute tasks concurrently
    tasks = [simulate_client(i) for i in range(1, NUM_CLIENTS + 1)]
    await asyncio.gather(*tasks)
    
    print(f"Stress test completed in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())