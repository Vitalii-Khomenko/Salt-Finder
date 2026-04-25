import unittest
import sys
import os

# Add parent directory to path to import the script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hashcat_pipe_runner import format_time

class TestHashcatRunner(unittest.TestCase):
    def test_format_time(self):
        self.assertEqual(format_time(30), "30.0 seconds")
        self.assertEqual(format_time(120), "2.0 minutes")
        self.assertEqual(format_time(3600), "1.0 hours")
        self.assertEqual(format_time(86400), "1.0 days")

if __name__ == '__main__':
    unittest.main()
