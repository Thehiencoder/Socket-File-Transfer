import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def corrupt_file(filepath: str, offset: int = 10):
    """Intentionally modify 1 byte in a file to test checksum mismatch errors."""
    if not os.path.exists(filepath):
        print(f"File {filepath} does not exist.")
        return
        
    with open(filepath, "r+b") as f:
        f.seek(offset)
        byte = f.read(1)
        if byte:
            # Flip bits of the byte
            corrupted_byte = bytes([byte[0] ^ 0xFF])
            f.seek(offset)
            f.write(corrupted_byte)
            print(f"Corrupted 1 byte at offset {offset} in {filepath}")
        else:
            print("File too small to corrupt at specified offset.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python corrupt_file.py <filepath>")
    else:
        corrupt_file(sys.argv[1])