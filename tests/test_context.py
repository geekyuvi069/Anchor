import unittest
import tempfile
import shutil
import os
from pathlib import Path
from anchor.context import generate_repo_map

class TestContext(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)
        
        # Create a sample python file
        (self.root / "sample.py").write_text(
            "class MyClass:\n    def my_method(self):\n        pass\n\ndef my_func():\n    pass\n", 
            encoding="utf-8"
        )
        
        # Create a file to ignore
        (self.root / "__pycache__").mkdir()
        (self.root / "__pycache__" / "cache.pyc").touch()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_repo_map_generation(self):
        repo_map = generate_repo_map(self.test_dir)
        
        self.assertIn("- sample.py", repo_map)
        self.assertIn("  class MyClass", repo_map)
        self.assertIn("  def my_method", repo_map)
        self.assertIn("  def my_func", repo_map)
        
        self.assertNotIn("__pycache__", repo_map)

if __name__ == '__main__':
    unittest.main()
