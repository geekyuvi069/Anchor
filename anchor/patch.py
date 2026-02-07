import whatthepatch
import patch_ng
from typing import Optional

class PatchError(Exception):
    pass

def apply_patch_dry_run(original_content: str, diff_text: str) -> str:
    """
    Applies a unified diff to a string in memory.
    Prioritizes robust parsing to handle AI-generated diffs with incorrect headers.
    """
    lines = original_content.splitlines()
    
    # 1. Manually parse the hunk to include ALL lines even if headers are wrong.
    hunk_lines = []
    in_hunk = False
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            in_hunk = True
            continue
        if in_hunk:
            if line.startswith((" ", "+", "-")):
                hunk_lines.append(line)
            elif not line.strip():
                 hunk_lines.append(" ") # Handle empty context lines
            else:
                if line.startswith("---") or line.startswith("+++"):
                    continue
                if line.strip() == "```":
                    break
    
    if not hunk_lines:
        # Try whatthepatch as a last resort
        try:
            diffs = list(whatthepatch.parse_patch(diff_text))
            if diffs and diffs[0].changes:
                new_lines = whatthepatch.apply_diff(diffs[0], lines)
                if new_lines:
                    return "\n".join(new_lines)
        except Exception:
            pass
        raise PatchError("Could not find any changes in the diff.")

    # Build old (search) and new (replacement) blocks
    search_block = []
    replace_block = []
    has_actual_changes = False
    for line in hunk_lines:
        prefix = line[0] if line else " "
        content = line[1:] if line else ""
        
        if prefix == " ":
            search_block.append(content)
            replace_block.append(content)
        elif prefix == "-":
            search_block.append(content)
            has_actual_changes = True
        elif prefix == "+":
            replace_block.append(content)
            has_actual_changes = True

    if not has_actual_changes:
        raise PatchError("Diff contains no additions or deletions.")

    # Search for the block in the original content
    orig_lines_clean = [l.strip() for l in lines]
    search_clean = [l.strip() for l in search_block if l.strip()]
    
    if not search_clean:
         # Pure addition (no context). Append to end.
         return original_content.rstrip() + "\n" + "\n".join(replace_block)

    # Fuzzy Search: match the context lines
    n = len(search_clean)
    match_index = -1
    for i in range(len(orig_lines_clean) - n + 1):
        if orig_lines_clean[i : i + n] == search_clean:
            match_index = i
            break
            
    if match_index != -1:
        # Map cleaned lines back to original indices
        orig_indices = []
        for idx, l in enumerate(lines):
            if l.strip():
                orig_indices.append(idx)
        
        if len(orig_indices) < match_index + n:
             # Fallback if indexing is weird
             return original_content.replace("\n".join(search_block), "\n".join(replace_block))
             
        start_idx = orig_indices[match_index]
        end_idx = orig_indices[match_index + n - 1]
        
        pre = lines[:start_idx]
        post = lines[end_idx + 1:]
        return "\n".join(pre + replace_block + post)

    # Final fallback: simple string replacement if fuzzy match failed
    search_str = "\n".join(search_block)
    if search_str and search_str in original_content:
        return original_content.replace(search_str, "\n".join(replace_block))

    raise PatchError("Could not find matching context in the file for the suggested changes.")

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
