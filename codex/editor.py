import os
import subprocess
import tempfile


def open_editor(initial_text: str = "") -> str:
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, prefix="codex_"
    ) as f:
        f.write(initial_text)
        tmp_path = f.name
    try:
        subprocess.run([editor, tmp_path], check=False)
        with open(tmp_path, "r") as f:
            return f.read().strip()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
