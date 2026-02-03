import os
import ast
from pathlib import Path
from typing import List, Set

IGNORE_DIRS = {'.git', '__pycache__', 'venv', '.env', '.idea', '.vscode', 'node_modules', 'dist', 'build'}
IGNORE_FILES = {'.DS_Store', 'poetry.lock', 'package-lock.json'}

def get_definitions(file_path: Path) -> List[str]:
    """Extract class and function definitions from a Python file."""
    definitions = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                definitions.append(f"class {node.name}")
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        definitions.append(f"  def {item.name}")
            elif isinstance(node, ast.FunctionDef):
                definitions.append(f"def {node.name}")
    except Exception:
        # If AST parsing fails (e.g. syntax error or non-python file masked as .py), skip
        return []
    return definitions

def generate_repo_map(root_dir: str = ".") -> str:
    """
    Generates a text-based map of the repository.
    Lists files and their classes/functions for .py files.
    """
    repo_map = []
    root_path = Path(root_dir).resolve()

    for root, dirs, files in os.walk(root_path):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        rel_root = Path(root).relative_to(root_path)
        if rel_root == Path('.'):
            level_str = ""
        else:
            level_str = str(rel_root) + "/"
            
        for file in files:
            if file in IGNORE_FILES or file.startswith('.'):
                continue
            
            full_path = Path(root) / file
            rel_path = rel_root / file
            
            repo_map.append(f"- {rel_path}")
            
            if file.endswith(".py"):
                defs = get_definitions(full_path)
                for d in defs:
                    repo_map.append(f"  {d}")
                    
    return "\n".join(repo_map) 