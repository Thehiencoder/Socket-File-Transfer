import struct
from common.framing import send_all, recv_exact

def send_command(sock, cmd_str: str):
    """Send a length-prefixed text command (4-byte length prefix)."""
    cmd_bytes = cmd_str.encode('utf-8')
    length_prefix = struct.pack("!I", len(cmd_bytes))
    send_all(sock, length_prefix + cmd_bytes)

def recv_command(sock) -> str:
    """Receive a length-prefixed text command (4-byte length prefix)."""
    length_bytes = recv_exact(sock, 4)
    if not length_bytes:
        return ""
    cmd_length = struct.unpack("!I", length_bytes)[0]
    cmd_bytes = recv_exact(sock, cmd_length)
    return cmd_bytes.decode('utf-8')

def send_file_chunk(sock, chunk: bytes):
    """Send a length-prefixed file chunk (8-byte length prefix)."""
    length_prefix = struct.pack("!Q", len(chunk))
    send_all(sock, length_prefix + chunk)

def recv_file_chunk(sock) -> bytes:
    """Receive a length-prefixed file chunk."""
    length_bytes = recv_exact(sock, 8)
    if not length_bytes:
        return b""
    chunk_length = struct.unpack("!Q", length_bytes)[0]
    return recv_exact(sock, chunk_length)