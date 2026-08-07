import socket
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PORT, HOST
from src.protocol import Opcode, pack_upload_req
import struct

def test_disconnect_binary():
    """Test client disconnection mid-transfer during binary UPLOAD_REQ."""
    print("Testing disconnect during binary UPLOAD_REQ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        print("Connected.")
        
        # Simulate login handshake
        login_payload = b"test_user"
        login_header = struct.pack("!IHH", len(login_payload), Opcode.LOGIN, 0)
        sock.sendall(login_header + login_payload)
        
        # Receive login ACK
        time.sleep(0.5)
        
        # Send UPLOAD_REQ but disconnect before finishing the payload transmission
        filename = "test_resume.dat"
        file_size = 1024 * 1024  # 1MB
        req_payload = pack_upload_req(file_size, filename)
        
        # Send header and only a partial payload (first 5 bytes)
        header = struct.pack("!IHH", len(req_payload), Opcode.UPLOAD_REQ, 1)
        sock.sendall(header + req_payload[:5])
        
        time.sleep(1)
        sock.close()
        print("Disconnected mid-command. Server should not crash and should log connection reset.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_disconnect_binary()