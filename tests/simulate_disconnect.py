import socket
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PORT, HOST
from src.phase1.protocol import send_command, recv_command

def test_disconnect():
    """Test immediate client disconnection right after establishing a connection."""
    print("Testing immediate disconnect...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        print("Connected.")
        # Disconnect immediately without sending any data
        sock.close()
        print("Disconnected. Server should not crash.")
    except Exception as e:
        print(f"Error: {e}")
        
def test_disconnect_mid_transfer():
    """Test client disconnection in the middle of sending a framed command."""
    print("Testing disconnect during command...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
        print("Connected.")
        # Send half of a command (4-byte length prefix specifying 10 bytes, but only sending 4 payload bytes)
        sock.sendall(b"\x00\x00\x00\x0aUPLO")
        time.sleep(1)
        sock.close()
        print("Disconnected mid-command. Server should not crash.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_disconnect()
    time.sleep(1)
    test_disconnect_mid_transfer()