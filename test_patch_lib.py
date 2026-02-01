import whatthepatch
import patch_ng
import io

original = """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    pass # TODO: Implement this
"""

diff = """--- sample_calculator.py
+++ sample_calculator.py
@@ -3,7 +3,7 @@
 def subtract(a, b):
     return a - b

-def multiply(a, b):
+def multiply(a, b):
     pass # TODO: Implement this
"""

print("--- Testing whatthepatch ---")
try:
    diffs = list(whatthepatch.parse_patch(diff))
    new_lines = whatthepatch.apply_diff(diffs[0], original.splitlines())
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")

print("\n--- Testing patch_ng ---")
try:
    # patch_ng usually works from file/set, let's explore
    # It has a PatchSet or internal from_string?
    # Checking source via dir() if I rely on installed lib
    pset = patch_ng.fromstring(diff.encode('utf-8'))
    if pset:
        print("Parsed successfully.")
        # Attempt apply. PatchSet usually needs a root location?
        # Or does it apply to stream?
        # Let's see if pset has apply.
        if hasattr(pset, 'apply'):
            pset.apply() # Might need arguments
            print("Apply method exists")
        else:
            # Maybe it returns list of patches
            print(f"Type: {type(pset)}")
    else:
        print("Failed to parse.")
except Exception as e:
    print(f"Failed patch_ng: {e}")
