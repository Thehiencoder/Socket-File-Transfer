import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.checksum import calculate_checksum

class TestChecksum(unittest.TestCase):
    def setUp(self):
        """Set up a temporary file before each test case."""
        self.test_file = "test_checksum.txt"
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("Hello World! This is a test file for checksum.")

    def tearDown(self):
        """Clean up the temporary file after each test case."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_checksum_consistency(self):
        # Verify that checksum results remain identical regardless of chunk size
        checksum1 = calculate_checksum(self.test_file, chunk_size=10)
        checksum2 = calculate_checksum(self.test_file, chunk_size=1024)
        self.assertEqual(checksum1, checksum2)
        
    def test_checksum_not_found(self):
        # Verify that calculating checksum for a non-existent file returns an empty string
        self.assertEqual(calculate_checksum("non_existent_file.txt"), "")

if __name__ == '__main__':
    unittest.main()