import typer
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from anchor.context import generate_repo_map
from anchor.llm import LLMClient
from anchor.patch import apply_patch_dry_run, validate_syntax, PatchError
from anchor.backup import BackupManager

app = typer.Typer(help="Anchor: Safe, local AI code editing.")
console = Console()

@app.command()
def edit(
    file: str,
    task: str,
    model: str = typer.Option("codellama", help="Ollama model to use"),
):
    """
    Edit a file based on a task description using local AI.
    """
    file_path = Path(file).resolve()
    if not file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File '{file}' not found.")
        raise typer.Exit(code=1)

    console.print(Panel(f"⚓ Anchor is working on: [bold]{file}[/bold]\nTask: {task}", title="Anchor CLI"))
    
    # 1. Context
    with console.status("[bold green]Generating context...[/bold green]"):
        repo_map = generate_repo_map(str(file_path.parent)) # Use file's directory as root for now, or git root
        content = file_path.read_text(encoding="utf-8")
        
        # Add line numbers to content for LLM
        numbered_content = "\n".join([f"{i+1:4} | {line}" for i, line in enumerate(content.splitlines())])
    
    # 2. LLM Call
    system_prompt = (
        "You are an expert coding assistant. You are strictly forbidden from outputting conversational text.\n"
        "You must ONLY output a valid UNIFIED DIFF to solve the user task.\n"
        "Here is the repository structure:\n"
        f"{repo_map}\n\n"
        "Here is the content of the file you need to edit:\n"
        f"File: {file}\n"
        "```python\n"
        f"{numbered_content}\n"
        "```\n"
        "Output ONLY the unified diff. Ensure line numbers in the diff match the ORIGINAL file (ignore the line number prefix in the prompt context)."
    )
    
    client = LLMClient(model=model)
    with console.status("[bold blue]Thinking (Ollama)...[/bold blue]"):
        try:
            response = client.generate(system_prompt, task)
        except RuntimeError as e:
            console.print(f"[bold red]LLM Error:[/bold red] {e}")
            raise typer.Exit(code=1)

    # 3. Diff & Dry Run
    with console.status("[bold yellow]Processing Diff...[/bold yellow]"):
        try:
            # Clean response (sometimes LLMs wrap in markdown code blocks)
            diff_text = response
            if "```diff" in diff_text:
                diff_text = diff_text.split("```diff")[1].split("```")[0]
            elif "```" in diff_text:
                diff_text = diff_text.split("```")[1].split("```")[0]
            
            diff_text = diff_text.strip()
            if not diff_text:
                 console.print("[yellow]No changes suggested by LLM.[/yellow]")
                 raise typer.Exit(code=0)

            new_content = apply_patch_dry_run(content, diff_text)
        except PatchError as e:
            console.print(f"[bold red]Patch Error:[/bold red] {e}")
            console.print(Panel(diff_text, title="Raw Diff from LLM"))
            raise typer.Exit(code=1)

    # 4. Validation
    with console.status("[bold magenta]Validating Syntax...[/bold magenta]"):
        if not validate_syntax(new_content, str(file_path)):
            console.print("[bold red]Validation Failed:[/bold red] Generated code has syntax errors.")
            # Optionally show diff anyway or abort
            raise typer.Exit(code=1)

    # 5. Backup & Apply
    console.print("[bold green]Change verified.[/bold green] Creating backup...")
    backup_mgr = BackupManager()
    backup_path = backup_mgr.create_backup(str(file_path))
    console.print(f"Backup saved to: {backup_path}")
    
    file_path.write_text(new_content, encoding="utf-8")
    console.print(f"[bold green]Success![/bold green] Edited {file}.")

@app.command()
def undo():
    """
    Undo the last change made by Anchor.
    """
    backup_mgr = BackupManager()
    try:
        restored_file = backup_mgr.restore_last_backup()
        if restored_file:
            console.print(f"[bold green]Restored:[/bold green] {restored_file}")
        else:
            console.print("[yellow]No backups found to undo.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Undo Error:[/bold red] {e}")

if __name__ == "__main__":
    app()
