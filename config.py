import os

PORT = int(os.environ.get('PORT', 8080))
HOST = os.environ.get('HOST', '0.0.0.0')
CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', 16384))  # 16KB
MAX_CLIENTS = int(os.environ.get('MAX_CLIENTS', 10))
SPEED_LIMIT_KBPS = int(os.environ.get('SPEED_LIMIT_KBPS', 500))  # for phase 2
DUPLICATE_FILE_POLICY = os.environ.get('DUPLICATE_FILE_POLICY', 'overwrite') # overwrite | reject | rename
