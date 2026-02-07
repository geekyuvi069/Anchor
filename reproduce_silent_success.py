
import whatthepatch
from anchor.patch import apply_patch_dry_run

content = """def add(a, b):
    return a + b
"""

# A diff that looks like it adds something but maybe doesn't?
# Or a diff that whatthepatch might fail on, triggering fallback.
diff = """--- initial_file.py
+++ initial_file.py
@@ -1,2 +1,3 @@
 def add(a, b):
     return a + b
+
+def subtract(a, b):
+    return a - b
"""

print("--- Testing apply_patch_dry_run ---")
diffs = list(whatthepatch.parse_patch(diff))
print(f"Parsed {len(diffs)} diffs")
d = diffs[0]
print(f"Changes count: {len(d.changes)}")
for c in d.changes:
    print(f"  Old:{c.old} New:{c.new} Line:{repr(c.line)}")

try:
    print("\n--- Testing Robust Parser logic ---")
    hunk_lines = []
    in_hunk = False
    for line in diff.splitlines():
        print(f"Seeing line: {repr(line)}")
        if line.startswith("@@"):
            in_hunk = True
            continue
        if in_hunk:
            if line.startswith((" ", "+", "-")):
                hunk_lines.append(line)
            elif not line.strip():
                 hunk_lines.append(" ") 
            else:
                if line.startswith("---") or line.startswith("+++"):
                    continue
                break
    
    print(f"Extracted {len(hunk_lines)} hunk lines:")
    for hl in hunk_lines:
        print(f"  {repr(hl)}")

    new_content = apply_patch_dry_run(content, diff)
    print("\nFinal Resulting New Content:")
    print(repr(new_content))
except Exception as e:
    print(f"Error raised: {e}")
