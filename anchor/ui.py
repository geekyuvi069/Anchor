from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.box import ROUNDED, MINIMAL

def print_banner(console: Console):
    """
    Displays the Anchor banner and welcome message.
    Design: Serious, trustworthy, developer-focused.
    """
    
    # 1. ASCII Art Banner (Block/Pixel Style)
    # Using a "Block" font style for that retro/pixel look
    banner_ascii = r"""
█████╗ ███╗   ██╗ ██████╗██╗  ██╗ ██████╗ ██████╗ 
██╔══██╗████╗  ██║██╔════╝██║  ██║██╔═══██╗██╔══██╗
███████║██╔██╗ ██║██║     ███████║██║   ██║██████╔╝
██╔══██║██║╚██╗██║██║     ██╔══██║██║   ██║██╔══██╗
██║  ██║██║ ╚████║╚██████╗██║  ██║╚██████╔╝██║  ██║
╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
"""
    
    # Gradient simulation: Cyan -> Blue -> Purple
    # We can print it line by line with different colors or just use a cool style.
    # "bold cyan" is a safe, high-tech choice.
    
    # 2. Layout Elements
    tagline = Text("Safe, Local AI-Assisted Code Editing", style="italic color(153)")
    
    # Features
    feature_table = Table.grid(padding=(0, 2))
    feature_table.add_column(style="bold cyan", justify="left")
    feature_table.add_column(style="white")
    
    feature_table.add_row("•", "Uses a local LLM (Ollama)")
    feature_table.add_row("•", "Applies diff-based edits only")
    feature_table.add_row("•", "Includes Undo and safety checks")
    
    # Examples Panel
    example_text = Text()
    example_text.append("\nExamples:\n", style="bold cyan")
    example_text.append("  • anchor edit file.py --task \"add JWT auth\"\n", style="color(159)")
    example_text.append("  • anchor undo\n", style="yellow")
    example_text.append("  • anchor --help", style="dim")

    # Dashed/Pixel-like Box for Examples
    from rich.box import ASCII2
    example_panel = Panel(
        example_text,
        border_style="color(63)", # Purple/Blueish
        box=ASCII2,
        expand=False,
        padding=(0, 4)
    )

    # Main Grid Layout
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    
    # Banner with gradient-ish effect by coloring the text object
    # We can make the first half cyan and second half purple if we want strictly similar to image
    # But a solid bold cyan is cleaner for ASCII blocks usually.
    grid.add_row(Text(banner_ascii, style="bold cyan"))
    grid.add_row(tagline)
    grid.add_row(" ") # Spacer
    grid.add_row(feature_table)
    grid.add_row(" ") # Spacer
    grid.add_row(example_panel)
    grid.add_row(" ")

    console.print(grid)

def print_welcome_screen():
    console = Console()
    print_banner(console)

if __name__ == "__main__":
    print_welcome_screen()
