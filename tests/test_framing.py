import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.framing import recv_exact

class MockSocket:
    """Mock socket class simulating network data fragmentation and disconnection."""
    def __init__(self, data_chunks):
        self.data_chunks = data_chunks
        self.index = 0

    def recv(self, n):
        if self.index < len(self.data_chunks):
            chunk = self.data_chunks[self.index]
            self.index += 1
            # Simulate returning up to n bytes maximum
            ret = chunk[:n]
            if len(chunk) > n:
                self.data_chunks.insert(self.index, chunk[n:])
            return ret
        return b""

class TestFraming(unittest.TestCase):
    def test_recv_exact_complete(self):
        # Simulate data arriving in fragments
        mock_sock = MockSocket([b"Hello", b" ", b"World"])
        data = recv_exact(mock_sock, 11)
        self.assertEqual(data, b"Hello World")

    def test_recv_exact_incomplete(self):
        # Simulate unexpected disconnect mid-transfer
        mock_sock = MockSocket([b"Hello"])
        data = recv_exact(mock_sock, 10)
        self.assertEqual(data, b"Hello")  # Return partial data received before disconnect

if __name__ == '__main__':
    unittest.main()