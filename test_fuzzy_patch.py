import whatthepatch

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

def robust_apply(original_text, diff_text):
    diffs = list(whatthepatch.parse_patch(diff_text))
    if not diffs: return None
    diff = diffs[0]
    
    lines = original_text.splitlines()
    
    # Simple hunk processor
    # We want to reconstruct the "Old Block" and "New Block" from the changes
    old_block = []
    new_block = []
    
    first_change = diff.changes[0]
    print(f"DEBUG Change Object: {first_change} (Type: {type(first_change)})")
    
    for change in diff.changes:
        # Try object access or tuple unpacking based on inspection
        if isinstance(change, tuple):
             if len(change) == 3:
                 (old_ix, new_ix, line) = change
             else:
                 # Ensure we handle whatthepatch 0.0.6+ which might be different
                 (old_ix, new_ix, line) = change[:3] 
        else:
             old_ix = change.old
             new_ix = change.new
             line = change.line
        if old_ix is not None and new_ix is not None:
            # Context
            old_block.append(line)
            new_block.append(line)
        elif old_ix is not None:
            # Removed
            old_block.append(line)
        elif new_ix is not None:
            # Added
            new_block.append(line)
            
    # Naive approach: Assuming one continuous hunk for this example.
    # Real robust patcher handles multiple hunks.
    
    # Build the block of lines we want to match (ignoring empties)
    old_norm = [line.strip() for line in old_block if line.strip()]
    if not old_norm:
        # If we are only adding lines (old block empty), we fallback to strict line number?
        # Or LLM messed up. For now assume we have context.
        return original_text 

    # Prepare original file: remove empties but keep track of indices
    orig_map = [] # List of (content, original_index)
    for idx, line in enumerate(lines):
        s = line.strip()
        if s:
            orig_map.append((s, idx))
            
    # Search for the sequence
    match_start_index = -1
    
    # We search in the 'content' part of orig_map
    orig_contents = [x[0] for x in orig_map]
    
    n = len(old_norm)
    for i in range(len(orig_contents) - n + 1):
        if orig_contents[i : i+n] == old_norm:
            match_start_index = i
            break
            
    if match_start_index != -1:
        # Found match!
        # Reconstruct the range in original file
        start_line_idx = orig_map[match_start_index][1]
        end_line_idx = orig_map[match_start_index + n - 1][1]
        
        print(f"Found fuzzy match at original lines {start_line_idx}-{end_line_idx}")
        
        # We replace everything from start_line_idx to end_line_idx with new_block
        # new_block is list of lines.
        
        pre = lines[:start_line_idx]
        post = lines[end_line_idx + 1:]
        
        new_content = "\n".join(pre + new_block + post)
        return new_content
    
    return "Failed to match context (fuzzy)"

if __name__ == "__main__":
    res = robust_apply(original, diff)
    print("\nResult:")
    print(res)
