import os
import threading

# Lock per filename to prevent threads from overwriting each other (initialized for Phase 2 usage)
_file_locks = {}
_locks_lock = threading.Lock()

def get_file_lock(filepath: str):
    """Retrieve or create a thread lock specific to a file path."""
    with _locks_lock:
        if filepath not in _file_locks:
            _file_locks[filepath] = threading.Lock()
        return _file_locks[filepath]

def sanitize_filename(filename: str) -> str:
    """Prevent directory traversal attacks."""
    # Get the base filename, stripping any directory paths
    return os.path.basename(filename)

def get_safe_path(storage_dir: str, filename: str, username: str = "default") -> str:
    """Generate a safe absolute path for reading/writing, partitioned by username."""
    safe_name = sanitize_filename(filename)
    safe_user = sanitize_filename(username)
    user_dir = os.path.join(os.path.abspath(storage_dir), safe_user)
    os.makedirs(user_dir, exist_ok=True)
    # Join with user directory to ensure safety and isolation
    return os.path.join(user_dir, safe_name)

def read_file_chunk(filepath: str, offset: int, chunk_size: int) -> bytes:
    """Read a chunk of data from a specific offset."""
    lock = get_file_lock(filepath)
    with lock:
        if not os.path.exists(filepath):
            return b""
        with open(filepath, "rb") as f:
            f.seek(offset)
            return f.read(chunk_size)

def write_file_chunk(filepath: str, offset: int, data: bytes) -> None:
    """Write a chunk of data at a specific offset."""
    lock = get_file_lock(filepath)
    with lock:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        # Open in "r+b" mode if file exists to allow seek, otherwise create with "w+b"
        mode = "r+b" if os.path.exists(filepath) else "w+b"
        with open(filepath, mode) as f:
            f.seek(offset)
            f.write(data)

def get_file_size(filepath: str) -> int:
    """Get file size in bytes."""
    if os.path.exists(filepath):
        return os.path.getsize(filepath)
    return 0