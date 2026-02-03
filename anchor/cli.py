import typer
import os
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

        # Add line numbers (empty if new file)
        numbered_content = "\n".join(
            [f"{i + 1:4} | {line}" for i, line in enumerate(content.splitlines())]
        )

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
    with console.status("[bold yellow]Processing...[/bold yellow]"):
        try:
            # Clean response
            clean_text = response
            if "```" in clean_text:
                import re

                # Priority 1: Look for explicit python block
                match = re.search(r"```python\n(.*?)(?:```|$)", clean_text, re.DOTALL)
                if match:
                    clean_text = match.group(1)
                else:
                    # Priority 2: Look for first generic block (if python block missing)
                    match = re.search(
                        r"```(?:\w+)?\n(.*?)(?:```|$)", clean_text, re.DOTALL
                    )
                    if match:
                        clean_text = match.group(1)

            clean_text = clean_text.strip()

            if new_file_mode:
                # For new files, the response IS the content
                new_content = clean_text
            else:
                # For existing files, it's a diff
                if not clean_text:
                    console.print("[yellow]No changes suggested by LLM.[/yellow]")
                    raise typer.Exit(code=0)
                new_content = apply_patch_dry_run(content, clean_text)

        except PatchError as e:
            console.print(f"[bold red]Patch Error:[/bold red] {e}")
            from rich.syntax import Syntax

            # Use specific lexer or 'text' to avoid treating [] as markup
            console.print(Panel(clean_text, title="Raw Output from LLM (Patch Error)"))
            raise typer.Exit(code=1)

    # 4. Validation
    with console.status("[bold magenta]Validating Syntax...[/bold magenta]"):
        if not validate_syntax(new_content, str(file_path)):
            console.print(
                "[bold red]Validation Failed:[/bold red] Generated code has syntax errors."
            )
            # Use Syntax to safely display code without markup errors
            from rich.syntax import Syntax

            syntax = Syntax(new_content, "python", theme="monokai", line_numbers=True)
            console.print(
                Panel(syntax, title="Invalid Code Content", border_style="red")
            )
            raise typer.Exit(code=1)

    # 5. Backup & Apply
    console.print("[bold green]Change verified.[/bold green] Creating backup...")
    backup_mgr = BackupManager()
    backup_path = backup_mgr.create_backup(str(file_path))
    console.print(f"Backup saved to: {backup_path}")

    file_path.write_text(new_content, encoding="utf-8")
    console.print(f"[bold green]Success![/bold green] Edited {file}.")


@app.command()
def modify(
    feature: str = typer.Option(..., "--feature", "-f", help="Feature description to implement"),
    file: str = typer.Option(None, help="Specific file to focus on (optional)"),
    model: str = typer.Option("codellama", help="Ollama model to use"),
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
    # Note: For now, we'll ask the LLM to generate the final diffs/code based on the plan.
    if buffer.current_phase == ConversationPhase.EDIT:
        if not file:
            file = Prompt.ask("[bold yellow]Which file should I apply these changes to?[/bold yellow]")
        
        file_path = Path(file).resolve()
        content = file_path.read_text(encoding="utf-8")
        numbered_content = "\n".join([f"{i+1:4} | {line}" for i, line in enumerate(content.splitlines())])

        with console.status(f"[bold blue]Generating changes for {file}...[/bold blue]"):
            edit_prompt = (
                f"Based on the following plan, generate a UNIFIED DIFF for {file}.\n"
                f"Plan:\n{buffer.implementation_plan}\n\n"
                f"Current File Content:\n```python\n{numbered_content}\n```\n"
                "Output ONLY the unified diff."
            )
            response = client.generate("You are an expert coder. Output ONLY a valid UNIFIED DIFF.", edit_prompt)

        # Reuse existing logic for processing diffs
        # (This is simplified - in a real app you might want to refactor the logic from 'edit' into a shared helper)
        try:
            clean_text = response
            if "```" in clean_text:
                import re
                match = re.search(r"```(?:diff|patch)?\n(.*?)(?:```|$)", clean_text, re.DOTALL)
                if match:
                    clean_text = match.group(1)
            
            clean_text = clean_text.strip()
            new_content = apply_patch_dry_run(content, clean_text)

            # Validation
            if apply_patch_dry_run(content, clean_text): # Just checking it doesn't fail
                 # Backup & Apply
                backup_mgr = BackupManager()
                backup_path = backup_mgr.create_backup(str(file_path))
                file_path.write_text(new_content, encoding="utf-8")
                console.print(f"[bold green]Success![/bold green] Applied changes to {file}.")
                console.print(f"Backup saved to: {backup_path}")
            
        except Exception as e:
            console.print(f"[bold red]Error applying changes:[/bold red] {e}")
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
