import sys
from pathlib import Path
from typing import Iterable

class LiveCodeWriter:
    """
    Handles real-time, token-by-token writing of code to a file.
    Mirrors output to the terminal as tokens arrive.
    """

    def __init__(self, file_path: str, quiet: bool = True):
        self.file_path = Path(file_path).resolve()
        self.quiet = quiet
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
    def write_stream(self, token_stream: Iterable[str]):
        """
        Consumes a token stream, writing each token to the file.
        Strips markdown code blocks and file headers.
        """
        buffer = ""
        with open(self.file_path, "w", encoding="utf-8") as f:
            for token in token_stream:
                # 1. Strip markdown code block markers
                clean_token = token.replace("```python", "").replace("```", "")
                
                # 2. Write to file
                f.write(clean_token)
                f.flush()
                
                # 3. Mirror to terminal ONLY if not quiet
                if not self.quiet:
                    sys.stdout.write(clean_token)
                    sys.stdout.flush()
        
        from rich import print as rprint
        rprint(f"\n\n[bold green]Success![/bold green] Content written to {self.file_path.name}")
