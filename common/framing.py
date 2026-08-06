import socket

def send_all(sock: socket.socket, data: bytes):
    """Send all data, ensuring no bytes are left behind."""
    sock.sendall(data)

def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes from the socket.
    
    Returns empty or partial bytes if the client disconnects prematurely.
    """
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            # Connection closed
            break
        data.extend(packet)
    return bytes(data)