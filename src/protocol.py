import struct
import asyncio
from common.framing import send_all, recv_exact, async_recv_exact

class Opcode:
    LOGIN = 1
    LIST_REQ = 2
    LIST_RESP = 3
    UPLOAD_REQ = 4
    DOWNLOAD_REQ = 5
    FILE_CHUNK = 6
    CHECKSUM_REQ = 7
    CHECKSUM_RESP = 8
    ACK = 9
    ERROR = 10

def send_binary_packet(sock, opcode: int, user_id: int, payload: bytes):
    """
    Pack and send a binary packet.
    8-byte Header format: [Length(4)] [Opcode(2)] [UserID(2)]
    """
    length = len(payload)
    header = struct.pack("!IHH", length, opcode, user_id)
    send_all(sock, header + payload)

def recv_binary_packet(sock):
    """
    Receive and unpack a binary packet.
    Returns Tuple (opcode, user_id, payload)
    """
    header_bytes = recv_exact(sock, 8)
    if not header_bytes:
        return None, None, None
        
    length, opcode, user_id = struct.unpack("!IHH", header_bytes)
    payload = recv_exact(sock, length) if length > 0 else b""
    return opcode, user_id, payload

# Utility functions for easier calling by client/server
def send_text_payload(sock, opcode: int, user_id: int, text: str):
    """Encode and send a text string inside a binary packet payload."""
    payload = text.encode('utf-8')
    send_binary_packet(sock, opcode, user_id, payload)

def recv_text_payload(payload: bytes) -> str:
    """Decode a text payload from bytes to string."""
    return payload.decode('utf-8')

# Specialized packing/unpacking helpers
def pack_upload_req(file_size: int, filename: str) -> bytes:
    """Pack upload request payload: 8-byte file size + UTF-8 encoded filename."""
    return struct.pack("!Q", file_size) + filename.encode('utf-8')

def unpack_upload_req(payload: bytes):
    """Unpack upload request payload into file_size and filename."""
    file_size = struct.unpack("!Q", payload[:8])[0]
    filename = payload[8:].decode('utf-8')
    return file_size, filename

def pack_ack_offset(offset: int) -> bytes:
    """Pack an 8-byte file offset into binary format."""
    return struct.pack("!Q", offset)

def unpack_ack_offset(payload: bytes) -> int:
    """Unpack an 8-byte file offset from binary payload."""
    return struct.unpack("!Q", payload)[0]

# --- ASYNC VERSIONS ---
async def recv_binary_packet_async(reader: asyncio.StreamReader):
    """
    Receive and unpack a binary packet asynchronously.
    Returns Tuple (opcode, user_id, payload)
    """
    header = await async_recv_exact(reader, 8)
    if not header or len(header) < 8:
        return None, None, None
    length, opcode, user_id = struct.unpack("!IHH", header)
    payload = await async_recv_exact(reader, length) if length > 0 else b""
    return opcode, user_id, payload

async def send_binary_packet_async(writer: asyncio.StreamWriter, opcode: int, user_id: int, payload: bytes):
    """
    Pack and send a binary packet asynchronously.
    """
    length = len(payload)
    header = struct.pack("!IHH", length, opcode, user_id)
    writer.write(header + payload)
    await writer.drain()

async def send_text_payload_async(writer: asyncio.StreamWriter, opcode: int, user_id: int, text: str):
    """Encode and send a text string inside a binary packet payload asynchronously."""
    await send_binary_packet_async(writer, opcode, user_id, text.encode('utf-8'))