# Anchor ⚓

**Anchor** is a safe, local AI-assisted code editing tool. It brings the power of LLMs (like Code Llama) to your terminal without sending your code to the cloud.

```text
█████╗ ███╗   ██╗ ██████╗██╗  ██╗ ██████╗ ██████╗ 
██╔══██╗████╗  ██║██╔════╝██║  ██║██╔═══██╗██╔══██╗
███████║██╔██╗ ██║██║     ███████║██║   ██║██████╔╝
██╔══██║██║╚██╗██║██║     ██╔══██║██║   ██║██╔══██╗
██║  ██║██║ ╚████║╚██████╗██║  ██║╚██████╔╝██║  ██║
╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝

Safe, Local AI-Assisted Code Editing
```

## 🚀 Vision

- **Local**: Runs entirely offline using [Ollama](https://ollama.ai). No data leaks.
- **Safe**: Validates every diff. Never modifies code blindly.
- **Controlled**: Instant `undo` if you don't like the change.

## 📦 Installation (Global)

To run `anchor` from any terminal window:

### Option 1: Using Pipx (Recommended)
```bash
pipx install .
```

### Option 2: Manual Setup (If pipx fails)
If you are on a restricted system (like Debian/Ubuntu), create a wrapper script:

```bash
# 1. Create the executable script
echo '#!/bin/bash' > ~/.local/bin/anchor
echo 'PYTHONPATH=/home/geekyuvi/Anchor /home/geekyuvi/Anchor/venv/bin/python3 -m anchor.cli "$@"' >> ~/.local/bin/anchor

# 2. Make it executable
chmod +x ~/.local/bin/anchor

# 3. Verify it works
anchor
```

## 💻 Usage

### 1. Welcome Screen
Just type `anchor` to see the status and help.
```bash
anchor
```

### 2. Create or Edit Code
Ask Anchor to build something new or refactor existing code:
```bash
# Create a new game
anchor edit snake.py "Create a snake game using pygame"

# Edit an existing file
anchor edit main.py "Refactor the login function to use JWT"
```

### 3. Undo
Made a mistake? Revert instantly.
```bash
anchor undo
```

## 🏗️ Architecture
- **LLM**: Ollama (Code Llama / Qwen)
- **Engine**: Python AST + Custom Fuzzy Patching
- **UI**: Rich + Typer

---
*Built for safe, local coding.*
