# Anchor

**Anchor** is a local-first, safe, and controlled AI-assisted code editing tool for developers who care about security, context, and reliability.

## 🚀 Vision

AI-powered coding tools are powerful, but often unsafe or privacy-invasive. `Anchor` aims to solve this by being:
- **Local**: Runs entirely offline using [Ollama](https://ollama.ai) and Code Llama. No API keys, no cloud data leaks.
- **Safe**: Never modifies your code blindly. It uses a rigorous pipeline of **Diff -> Dry-run -> Validate -> Backup -> Apply**.
- **Context-Aware**: Understands your project structure (repo maps) without hallucinating file paths.
- **Controlled**: You always have an `undo` button.

## 🛠️ Features (v1)

- **CLI-First**: Simple, efficient command-line interface.
- **Unified Diffs**: The AI only suggests *changes*, it never rewrites entire files.
- **Safety Pipeline**:
    1. **Parse**: Validates the diff format.
    2. **Dry-Run**: Simulates the patch in memory.
    3. **Validate**: Checks syntax (e.g., `python -m py_compile`) before applying.
    4. **Backup**: Saves a copy of the original file.
- **Undo Support**: One-command rollback (`Anchor --undo`).

## 📦 Installation

*(Instructions for v1 development setup)*

1.  **Prerequisites**:
    *   Python 3.10+
    *   [Ollama](https://ollama.ai) installed and running.
    *   Pull the model: `ollama pull codellama`

2.  **Setup**:
    ```bash
    git clone https://github.com/yourusername/Anchor.git
    cd Anchor
    pip install -r requirements.txt
    ```

## 💻 Usage

### Editing Code
Ask `Anchor` to perform a task on a specific file:
```bash
python main.py edit <filename> --task "Add a docstring to the apply_patch function"
```

### Undo Changes
Made a mistake? Revert the last change instantly:
```bash
python main.py undo
```

## 🏗️ Architecture

- **LLM Engine**: Ollama (Code Llama)
- **Context**: Python AST (Abstract Syntax Tree) for repo structure
- **Patch Engine**: `patch-ng` / `whatthepatch`
- **CLI Framework**: Typer

## 🤝 Contributing

We welcome contributions! This is a tool for developers, by developers.

1.  Fork the repo.
2.  Create a feature branch.
3.  Submit a Pull Request.

---
*Built with ❤️ for safe, local AI coding.*
