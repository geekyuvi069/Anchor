import whatthepatch
import patch_ng
from typing import Optional

class PatchError(Exception):
    pass

def apply_patch_dry_run(original_content: str, diff_text: str) -> str:
    """
    Applies a unified diff to a string in memory.
    Returns the modified content or raises PatchError.
    """
    # Parse the diff
    try:
        diffs = list(whatthepatch.parse_patch(diff_text))
    except Exception as e:
        raise PatchError(f"Failed to parse diff: {e}")

    if not diffs:
        raise PatchError("No valid diff found in response.")

    # We expect the diff to target the file we are editing.
    # Since we are feeding context for ONE file, we assume the first diff is relevant.
    diff = diffs[0]
    
    if diff.header is None and diff.changes is None:
         raise PatchError("Diff is empty or invalid.")

    # Apply using patch_ng logic (which emulates GNU patch)
    # Since patch_ng applies to files, we use its internal logic or a wrapper if available.
    # Actually, patch_ng is a wrapper around the patch command or python implementation.
    # 'whatthepatch' can apply patches to text. Let's use whatthepatch for application if possible,
    # or implement a simple line-based patcher.
    
    # whatthepatch.apply_diff is available!
    try:
        new_lines = whatthepatch.apply_diff(diff, original_content.splitlines())
        return "\n".join(new_lines)
    except Exception as e:
        # Fallback to Fuzzy Patching
        lines = original_content.splitlines()
        
        # Build changes
        old_block = [] # Content of removed/context lines
        new_block = [] # Content of added/context lines
        
        for change in diff.changes:
            # Handle whatthepatch 0.x and 1.x differences if any, 
            # assume object access based on tests
            # change is object with 'old', 'new', 'line'
            old_ix = change.old
            new_ix = change.new
            line = change.line
            
            if old_ix is not None and new_ix is not None:
                old_block.append(line)
                new_block.append(line)
            elif old_ix is not None:
                old_block.append(line)
            elif new_ix is not None:
                new_block.append(line)
        
        # Normalize: remove empty lines for matching
        old_norm = [l.strip() for l in old_block if l.strip()]
        if not old_norm:
             raise PatchError(f"Strict patch failed and fuzzy patch cannot match empty context: {e}")
             
        # Map original non-empty lines
        orig_map = [] # (content, original_index)
        for idx, line in enumerate(lines):
            s = line.strip()
            if s:
                orig_map.append((s, idx))
                
        # Search
        orig_contents = [x[0] for x in orig_map]
        n = len(old_norm)
        match_start_index = -1
        
        for i in range(len(orig_contents) - n + 1):
            if orig_contents[i : i+n] == old_norm:
                match_start_index = i
                break
        
        if match_start_index != -1:
             start_line_idx = orig_map[match_start_index][1]
             end_line_idx = orig_map[match_start_index + n - 1][1]
             
             pre = lines[:start_line_idx]
             post = lines[end_line_idx + 1:]
             return "\n".join(pre + new_block + post)
             
        raise PatchError(f"Strict patch failed and fuzzy patch could not find context: {e}")

def validate_syntax(content: str, filename: str) -> bool:
    """
    Checks if the content is valid syntax for the given filename extension.
    Currently supports Python.
    """
    if filename.endswith(".py"):
        import ast
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False
    return True
