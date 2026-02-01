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
         raise PatchError(f"Failed to apply patch: {e}")

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
