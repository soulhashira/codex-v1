import json
from datetime import datetime
from pathlib import Path

from .crypto import encrypt, decrypt, WrongPassword

CODEX_DIR = Path.home() / ".codex"


def init():
    CODEX_DIR.mkdir(exist_ok=True)
    manifest = CODEX_DIR / "libraries.json"
    if not manifest.exists():
        manifest.write_text(json.dumps({"libraries": []}))


def get_libraries() -> list:
    manifest = CODEX_DIR / "libraries.json"
    return json.loads(manifest.read_text())["libraries"]


def library_exists(name: str) -> bool:
    return name in get_libraries()


def create_library(name: str, password: str):
    manifest_path = CODEX_DIR / "libraries.json"
    data = json.loads(manifest_path.read_text())
    data["libraries"].append(name)
    manifest_path.write_text(json.dumps(data))

    lib_dir = CODEX_DIR / name
    (lib_dir / "entries").mkdir(parents=True, exist_ok=True)
    (lib_dir / "indexes").mkdir(parents=True, exist_ok=True)

    meta = {"name": name, "indexes": [], "created": _now()}
    _write_meta(lib_dir / "library.meta", meta, password)


def open_library(name: str, password: str) -> dict:
    path = CODEX_DIR / name / "library.meta"
    return _read_meta(path, password)


def update_library_meta(library: str, password: str, meta: dict):
    path = CODEX_DIR / library / "library.meta"
    _write_meta(path, meta, password)


def index_exists(library: str, index: str) -> bool:
    path = CODEX_DIR / library / "indexes" / index / "index.meta"
    return path.exists()


def create_index(library: str, index: str, password: str):
    idx_dir = CODEX_DIR / library / "indexes" / index
    idx_dir.mkdir(parents=True, exist_ok=True)
    meta = {"name": index, "entries": [], "created": _now()}
    _write_meta(idx_dir / "index.meta", meta, password)


def open_index(library: str, index: str, password: str) -> dict:
    path = CODEX_DIR / library / "indexes" / index / "index.meta"
    return _read_meta(path, password)


def update_index(library: str, index: str, password: str, meta: dict):
    path = CODEX_DIR / library / "indexes" / index / "index.meta"
    _write_meta(path, meta, password)


def save_entry(library: str, entry_id: str, content: str, password: str):
    path = CODEX_DIR / library / "entries" / f"{entry_id}.enc"
    _write_meta(path, {"content": content, "saved": _now()}, password)


def load_entry(library: str, entry_id: str, password: str) -> str:
    path = CODEX_DIR / library / "entries" / f"{entry_id}.enc"
    data = _read_meta(path, password)
    return data["content"]


def _write_meta(path: Path, data: dict, password: str):
    raw = json.dumps(data).encode()
    path.write_bytes(encrypt(raw, password))


def _read_meta(path: Path, password: str) -> dict:
    raw = decrypt(path.read_bytes(), password)
    return json.loads(raw.decode())


def _now() -> str:
    return datetime.now().isoformat()
