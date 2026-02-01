import unittest
from anchor.patch import apply_patch_dry_run, validate_syntax, PatchError

class TestPatch(unittest.TestCase):
    def test_apply_patch_success(self):
        original = "def hello():\n    print('world')\n"
        diff = """--- sample.py
+++ sample.py
@@ -1,2 +1,2 @@
 def hello():
-    print('world')
+    print('anchor')
"""
        expected = "def hello():\n    print('anchor')"
        result = apply_patch_dry_run(original, diff)
        self.assertEqual(result.strip(), expected.strip())

    def test_apply_patch_invalid(self):
        original = "some content"
        diff = "invalid diff"
        with self.assertRaises(PatchError):
            apply_patch_dry_run(original, diff)

    def test_validate_syntax_valid(self):
        code = "def foo(): pass"
        self.assertTrue(validate_syntax(code, "test.py"))

    def test_validate_syntax_invalid(self):
        code = "def foo(): return @"
        self.assertFalse(validate_syntax(code, "test.py"))

if __name__ == '__main__':
    unittest.main()
