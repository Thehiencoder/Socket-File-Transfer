import hashlib
import os

def calculate_checksum(filepath: str, chunk_size: int = 16384) -> str:
    """Calculate the MD5 checksum of a file using streaming (without loading the entire file into RAM)."""
    if not os.path.exists(filepath):
        return ""
        
    md5_hash = hashlib.md5()
    with open(filepath, "rb") as f:
        # Read chunk by chunk and update the hash
        for byte_block in iter(lambda: f.read(chunk_size), b""):
            md5_hash.update(byte_block)
            
    return md5_hash.hexdigest()