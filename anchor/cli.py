import typer
import os
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm

from anchor.context import generate_repo_map
from anchor.llm import LLMClient
from anchor.patch import apply_patch_dry_run, validate_syntax, PatchError
from anchor.backup import BackupManager
from anchor.conversation import (
    ConversationBuffer,
    ConversationPhase,
    create_analysis_prompt,
    create_discussion_prompt,
    create_planning_prompt,
)
from anchor.streaming import LiveCodeWriter

def process_and_apply_diff(
    content: str, 
    raw_response: str, 
    file_path: Path, 
    console: Console,
    is_new_file: bool = False
) -> Optional[str]:
    """
    Shared helper to extract, apply, and validate a diff from LLM response.
    Returns the new content if successful, otherwise raises typer.Exit or returns None.
    """
    try:
        clean_text = raw_response
        if "```" in clean_text:
            import re
            # Priority 1: Look for explicit diff/patch/python block
            match = re.search(r"```(?:diff|patch|python|txt)?\n(.*?)(?:```|$)", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1)
            else:
                # Priority 2: Look for first generic block
                match = re.search(r"```(?:\w+)?\n(.*?)(?:```|$)", clean_text, re.DOTALL)
                if match:
                    clean_text = match.group(1)
        
        # FINAL CLEANUP: If it looks like a diff, try to find the start and end of it
        if "--- " in clean_text and "+++ " in clean_text:
             import re
             # Extract from first --- to end of last hunk
             match = re.search(r"(--- .*?@@.*?\n.*)", clean_text, re.DOTALL)
             if match:
                 clean_text = match.group(1)

        clean_text = clean_text.strip()

        if is_new_file:
            new_content = clean_text
        else:
            if not clean_text:
                console.print("[yellow]No changes suggested by LLM.[/yellow]")
                return None
            new_content = apply_patch_dry_run(content, clean_text)

        # Validation
        if not validate_syntax(new_content, str(file_path)):
            console.print("[bold red]Validation Failed:[/bold red] Generated code has syntax errors.")
            from rich.syntax import Syntax
            syntax = Syntax(new_content, "python", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="Invalid Code Content", border_style="red"))
            raise typer.Exit(code=1)

        return new_content

    except PatchError as e:
        console.print(f"[bold red]Patch Error:[/bold red] {e}")
        console.print(Panel(clean_text, title="Raw Output from LLM (Patch Error)"))
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error applying changes:[/bold red] {e}")
        raise typer.Exit(code=1)

app = typer.Typer(help="Anchor: Safe, local AI code editing.")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Anchor: Safe, local AI code editing.
    """
    if ctx.invoked_subcommand is None:
        from anchor.ui import print_banner

        print_banner(console)


@app.command()
def edit(
    file: str,
    task: str,
    model: str = typer.Option("codellama", help="Ollama model to use"),
    show_tokens: bool = typer.Option(False, "--show-tokens", help="Show code as it is written in the terminal"),
):
    """
    Edit a file based on a task description using local AI.
    """
    file_path = Path(file).resolve()
    new_file_mode = False

    if not file_path.exists():
        console.print(
            Panel(f"File '{file}' does not exist. Creating new file...", style="yellow")
        )
        file_path.touch()
        new_file_mode = True

    console.print(
        Panel(
            f"⚓ Anchor is working on: [bold]{file}[/bold]\nTask: {task}",
            title="Anchor CLI",
        )
    )

    # 1. Context
    with console.status("[bold green]Generating context...[/bold green]"):
        repo_map = generate_repo_map(str(file_path.parent))
        content = file_path.read_text(encoding="utf-8")

    # 2. LLM Call
    if new_file_mode:
        system_prompt = (
            "You are an expert coding assistant.\n"
            "The user wants to create a NEW file.\n"
            "You must output the FULL CONTENT of the file, starting with all necessary IMPORTS.\n"
            "The code must be complete and runnable. Do NOT output snippets.\n"
            "Do NOT use diffs. Output the raw code inside a single code block.\n"
            "Here is the project context:\n"
            f"{repo_map}\n"
        )
    else:
        system_prompt = (
            "You are an expert coding assistant. You are strictly forbidden from outputting conversational text.\n"
            "You must ONLY output a valid UNIFIED DIFF to solve the user task.\n"
            "CRITICAL: Do NOT include any commentary, headers like 'This file is generated', or terminal UI characters.\n"
            "CRITICAL: The context lines in your diff MUST EXACTLY MATCH the file content provided below.\n"
            "Here is the repository structure:\n"
            f"{repo_map}\n\n"
            "Here is the content of the file you need to edit:\n"
            f"File: {file}\n"
            "```python\n"
            f"{content}\n"
            "```\n"
            "Output ONLY the unified diff."
        )

    client = LLMClient(model=model)
    with console.status("[bold blue]Thinking (Ollama)...[/bold blue]"):
        try:
            response = client.generate(system_prompt, task)
        except RuntimeError as e:
            console.print(f"[bold red]LLM Error:[/bold red] {e}")
            raise typer.Exit(code=1)

    # 3. Diff & Dry Run & Validation
    with console.status("[bold yellow]Processing & Validating...[/bold yellow]"):
        new_content = process_and_apply_diff(
            content, 
            response, 
            file_path, 
            console, 
            is_new_file=new_file_mode
        )
        if new_content is None:
            raise typer.Exit(code=0)

    # 4. Backup & Apply (Steps 4 & 5 merged or renumbered)
    console.print("[bold green]Change verified.[/bold green] Creating backup...")
    backup_mgr = BackupManager()
    backup_path = backup_mgr.create_backup(str(file_path))
    console.print(f"Backup saved to: {backup_path}")

    if new_file_mode:
        # Stream the new file content for the "LiveCode" experience
        console.print(f"[bold blue]Streaming content to {file}...[/bold blue]")
        writer = LiveCodeWriter(str(file_path), quiet=not show_tokens)
        token_stream = client.stream_generate(system_prompt, task)
        writer.write_stream(token_stream)
    else:
        file_path.write_text(new_content, encoding="utf-8")
        console.print(f"[bold green]Success![/bold green] Edited {file}.")


@app.command()
def modify(
    feature: str = typer.Argument(..., help="Feature description to implement"),
    file: str = typer.Option(None, "--file", "-f", help="Specific file to focus on (optional)"),
    model: str = typer.Option("codellama", "--model", "-m", help="Ollama model to use"),
):
    """
    Modify code with a discussion phase first.
    Flow: Prompt -> Discuss (Loop) -> Plan -> Confirmation -> Edit -> Save
    """
    # 1. Context
    with console.status("[bold green]Analyzing project context...[/bold green]"):
        repo_map = generate_repo_map(".")
        focus_file_content = ""
        if file:
            file_path = Path(file).resolve()
            if file_path.exists():
                focus_file_content = f"\nFocused File ({file}):\n{file_path.read_text(encoding='utf-8')}"
        
        repo_context = f"{repo_map}\n{focus_file_content}"
        buffer = ConversationBuffer(feature_request=feature, context_summary=repo_context)
        client = LLMClient(model=model)

    # 2. Initial Analysis
    with console.status("[bold blue]Initial Analysis...[/bold blue]"):
        system_prompt = "You are a helpful coding assistant. Engage in a discussion to clarify the task before providing code."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": create_analysis_prompt(feature, repo_context)}
        ]
        response = client.chat(messages)
        buffer.add_message("assistant", response, ConversationPhase.DISCUSS)

    # 3. Discussion Loop
    while buffer.current_phase == ConversationPhase.DISCUSS:
        console.print(Panel(Markdown(response), title="[bold blue]Anchor's Analysis[/bold blue]"))
        
        user_input = Prompt.ask("\n[bold yellow]Your feedback (or type 'plan' to move to implementation)[/bold yellow]")
        
        if user_input.lower() == "plan":
            buffer.transition_to(ConversationPhase.PLAN)
            break
            
        buffer.add_message("user", user_input)
        
        with console.status("[bold blue]Thinking...[/bold blue]"):
            discussion_history = buffer.get_discussion_history()
            chat_messages = [
                {"role": "system", "content": system_prompt},
                *([{"role": m.role, "content": m.content} for m in buffer.messages[-5:]]) # Last 5 messages for context
            ]
            response = client.chat(chat_messages)
            buffer.add_message("assistant", response)

    # 4. Planning
    if buffer.current_phase == ConversationPhase.PLAN:
        with console.status("[bold magenta]Creating implementation plan...[/bold magenta]"):
            discussion_history = "\n".join([f"{m.role}: {m.content}" for m in buffer.messages])
            plan_prompt = create_planning_prompt(feature, discussion_history, repo_context)
            plan_response = client.chat([{"role": "user", "content": plan_prompt}])
            buffer.implementation_plan = plan_response
            buffer.transition_to(ConversationPhase.CONFIRM)

    if buffer.current_phase == ConversationPhase.CONFIRM:
        console.print(Panel(Markdown(buffer.implementation_plan), title="[bold magenta]Implementation Plan[/bold magenta]"))
        
        if not Confirm.ask("[bold green]Do you want to proceed with this plan?[/bold green]"):
            console.print("[yellow]Modification cancelled.[/yellow]")
            raise typer.Exit()
        
        buffer.confirmed = True
        buffer.transition_to(ConversationPhase.EDIT)

    # 5. Execution (Edit phase)
    if buffer.current_phase == ConversationPhase.EDIT:
        if not file:
            file = Prompt.ask("[bold yellow]Which file should I apply these changes to?[/bold yellow]")
        
        file_path = Path(file).resolve()
        content = file_path.read_text(encoding="utf-8")
        # Removing line numbers from content passed to LLM for diff generation
        # numbered_content = "\n".join([f"{i+1:4} | {line}" for i, line in enumerate(content.splitlines())])

        with console.status(f"[bold blue]Generating changes for {file}...[/bold blue]"):
            edit_prompt = (
                f"Based on the following plan, generate a UNIFIED DIFF for {file}.\n"
                f"Plan:\n{buffer.implementation_plan}\n\n"
                f"Current File Content:\n```python\n{content}\n```\n"
                "Output ONLY the unified diff. DO NOT hallucinate file headers or UI characters."
            )
            response = client.generate("You are an expert coder. Output ONLY a valid UNIFIED DIFF. Do NOT hallucinate headers.", edit_prompt)

        # Use shared helper
        with console.status("[bold yellow]Processing & Validating...[/bold yellow]"):
            new_content = process_and_apply_diff(content, response, file_path, console)
            
            if new_content:
                # Backup & Apply
                backup_mgr = BackupManager()
                backup_path = backup_mgr.create_backup(str(file_path))
                
                # For consistency, just write. If we wanted streaming here,
                # we'd have to stream the resulting content.
                file_path.write_text(new_content, encoding="utf-8")
                console.print(f"[bold green]Success![/bold green] Applied changes to {file}.")
                console.print(f"Backup saved to: {backup_path}")
            else:
                console.print("[yellow]No changes applied.[/yellow]")

@app.command()
def write(
    file: str = typer.Argument(..., help="Target file to write code into"),
    task: str = typer.Argument(..., help="Task description for the LLM"),
    model: str = typer.Option("codellama", help="Ollama model to use"),
    show_tokens: bool = typer.Option(False, "--show-tokens", help="Show code as it is written in the terminal"),
):
    """
    Generate code and write it to a file token-by-token in real-time.
    Exactly like human typing.
    """
    file_path = Path(file).resolve()
    if file_path.exists():
        if not Confirm.ask(f"[yellow]File {file} already exists. Overwrite?[/yellow]"):
            raise typer.Exit()
        backup_mgr = BackupManager()
        backup_mgr.create_backup(str(file_path))

    console.print(
        Panel(
            f"🚀 [bold]Anchor LiveWrite[/bold] is writing to: [bold]{file}[/bold]\nTask: {task}",
            title="LiveCode Writer",
            border_style="blue",
        )
    )

    client = LLMClient(model=model)
    writer = LiveCodeWriter(str(file_path), quiet=not show_tokens)

    system_prompt = (
        "You are an expert coding assistant.\n"
        "Generate ONLY the raw code requested. Do NOT use markdown code blocks (no ```). No commentary.\n"
        "The code must be complete and runnable."
    )

    try:
        token_stream = client.stream_generate(system_prompt, task)
        writer.write_stream(token_stream)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)
@app.command()
def chat(
    model: str = typer.Option("codellama", help="Ollama model to use"),
):
    """
    Start a general conversation with Anchor.
    """
    client = LLMClient(model=model)
    console.print(Panel("Welcome to Anchor Chat! Type [bold cyan]'exit'[/bold cyan] or [bold cyan]'quit'[/bold cyan] to end the session.", title="[bold cyan]Anchor Chat[/bold cyan]"))
    
    messages = [
        {"role": "system", "content": "You are Anchor, a helpful and friendly AI coding assistant. You can chat about anything, but you're especially good at programming."}
    ]
    
    while True:
        user_input = Prompt.ask("\n[bold yellow]You[/bold yellow]")
        
        if user_input.lower() in ["exit", "quit"]:
            console.print("[yellow]Goodbye![/yellow]")
            break
            
        messages.append({"role": "user", "content": user_input})
        
        with console.status("[bold blue]Anchor is typing...[/bold blue]"):
            try:
                response = client.chat(messages)
                console.print(f"\n[bold cyan]Anchor[/bold cyan]: {response}")
                messages.append({"role": "assistant", "content": response})
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                break

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
