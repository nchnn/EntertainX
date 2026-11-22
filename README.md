# EntertainX

Multi-category entertainment desktop app (Movies & TV Shows, Music, Games) built with PySide6.

---

## Prerequisites

- **Python**: `>= 3.12` (Python 3.12 recommended; `.python-version` pins to `3.12`).
- **UV**: Astral's fast Python package and environment manager.
  - **Windows (PowerShell)**:
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
  - **macOS / Linux**:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
  - **Via pip**:
    ```bash
    pip install uv
    ```

---

## Installation & Setup

Set up the project and virtual environment from a fresh clone with a single command:

```bash
uv sync
```

This will automatically:
1. Locate or download Python 3.12+.
2. Create and configure the `.venv` virtual environment.
3. Install all runtime and development dependencies locked in `uv.lock`.

---

## Running the Application

To launch EntertainX:

```bash
uv run main.py
```

`uv run` ensures the application executes within the managed `.venv` environment without needing manual shell activation.

---

## Development & Testing

Run the full test suite using `pytest`:

```bash
uv run pytest
```

---

## Managing Dependencies

EntertainX uses `pyproject.toml` and `uv.lock` for reproducible dependency management.

### Adding a runtime dependency:

```bash
uv add <package-name>
```

### Adding a development dependency:

```bash
uv add --dev <package-name>
```

### Removing a dependency:

```bash
uv remove <package-name>
```

### Updating dependencies:

To safely upgrade a specific package without upgrading the entire dependency tree:

```bash
uv lock --upgrade-package <package-name>
uv sync
```

---

## Legacy / Fallback Setup (`pip`)

For environments or tooling that require standard `pip`, `requirements.txt` is retained for compatibility:

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix:
source venv/bin/activate

pip install -r requirements.txt
python main.py
```
