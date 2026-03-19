import getpass
import sys
from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import editor, indexer, storage
from .crypto import WrongPassword

console = Console()


def main():
    storage.init()
    console.print(
        Panel(
            "[bold cyan]CODEX[/bold cyan]\nencrypted journal",
            border_style="cyan",
            width=40,
        )
    )
    while True:
        choice = _main_menu()
        if choice == "1":
            _select_library_flow()
        elif choice == "2":
            _create_library_flow()
        elif choice in ("q", "quit", "exit"):
            console.print("[dim]Exiting.[/dim]")
            sys.exit(0)
        else:
            console.print("[dim]Invalid choice.[/dim]")


# ── Menus ──────────────────────────────────────────────────────────────────────

def _main_menu() -> str:
    libraries = storage.get_libraries()
    lib_list = ", ".join(libraries) if libraries else "[dim]none[/dim]"
    console.print(f"\n[bold]Libraries:[/bold] {lib_list}")
    console.print("  [1] Open library")
    console.print("  [2] Create library")
    console.print("  [q] Quit")
    return input("> ").strip().lower()


def _library_menu(library: str, lib_password: str, lib_meta: dict):
    while True:
        indexes = lib_meta.get("indexes", [])
        idx_list = ", ".join(f"@{i}" for i in indexes) if indexes else "[dim]none[/dim]"
        console.print(f"\n[bold cyan]{library}[/bold cyan] — {idx_list}")
        console.print("  [1] New entry")
        console.print("  [2] Browse index")
        console.print("  [b] Back")
        choice = input("> ").strip().lower()

        if choice == "1":
            lib_meta = _new_entry_flow(library, lib_password, lib_meta)
        elif choice == "2":
            _browse_index_flow(library, lib_meta)
        elif choice == "b":
            break
        else:
            console.print("[dim]Invalid choice.[/dim]")


# ── Library flows ──────────────────────────────────────────────────────────────

def _create_library_flow():
    name = input("Library name: ").strip()
    if not name:
        return
    if storage.library_exists(name):
        console.print(f"[yellow]Library '{name}' already exists.[/yellow]")
        return
    password = getpass.getpass("Set library password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        console.print("[red]Passwords don't match.[/red]")
        return
    storage.create_library(name, password)
    console.print(f"[green]Library '{name}' created.[/green]")


def _select_library_flow():
    libraries = storage.get_libraries()
    if not libraries:
        console.print("[yellow]No libraries yet. Create one first.[/yellow]")
        return
    for i, lib in enumerate(libraries, 1):
        console.print(f"  [{i}] {lib}")
    choice = input("Select library: ").strip()
    try:
        name = libraries[int(choice) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        return

    password = getpass.getpass(f"Library password for '{name}': ")
    try:
        lib_meta = storage.open_library(name, password)
    except WrongPassword:
        console.print("[red]Wrong password.[/red]")
        return

    _library_menu(name, password, lib_meta)


# ── Entry flows ────────────────────────────────────────────────────────────────

def _new_entry_flow(library: str, lib_password: str, lib_meta: dict) -> dict:
    console.print(
        "[dim]Opening editor. Use @tags anywhere in your text to index the entry.[/dim]"
    )
    content = editor.open_editor()

    if not content.strip():
        console.print("[yellow]Empty entry — discarded.[/yellow]")
        return lib_meta

    tags = indexer.extract_tags(content)
    wc = indexer.word_count(content)
    entry_id = indexer.make_entry_id()

    console.print(
        f"\n[bold]Tags:[/bold] {' '.join(f'@{t}' for t in tags) if tags else '[dim]none[/dim]'}"
    )
    console.print(f"[bold]Words:[/bold] {wc}")

    if not tags:
        console.print(
            "[yellow]No @tags found. Entry won't appear in any index.[/yellow]"
        )
        if input("Save anyway? [y/N] ").strip().lower() != "y":
            return lib_meta

    # Collect index passwords
    index_passwords = {}
    new_indexes = []

    for tag in tags:
        if storage.index_exists(library, tag):
            pw = getpass.getpass(f"Index password for @{tag}: ")
            try:
                storage.open_index(library, tag, pw)
                index_passwords[tag] = pw
            except WrongPassword:
                console.print(
                    f"[red]Wrong password for @{tag} — skipping this index.[/red]"
                )
        else:
            console.print(f"[green]New index @{tag} — set a password.[/green]")
            pw = getpass.getpass(f"Set password for @{tag}: ")
            confirm = getpass.getpass("Confirm: ")
            if pw != confirm:
                console.print(f"[red]Passwords don't match — skipping @{tag}.[/red]")
                continue
            index_passwords[tag] = pw
            new_indexes.append(tag)

    # Document password
    doc_password = getpass.getpass("Set document password: ")
    confirm = getpass.getpass("Confirm document password: ")
    if doc_password != confirm:
        console.print("[red]Document passwords don't match — entry discarded.[/red]")
        return lib_meta

    # Save encrypted entry
    storage.save_entry(library, entry_id, content, doc_password)

    # Create any new indexes
    for tag in new_indexes:
        storage.create_index(library, tag, index_passwords[tag])

    # Build entry metadata record
    entry_meta = {
        "id": entry_id,
        "date": datetime.now().isoformat(),
        "word_count": wc,
        "tags": tags,
        "preview": indexer.preview(content),
    }

    # Update each index
    for tag in tags:
        if tag not in index_passwords:
            continue
        idx_meta = storage.open_index(library, tag, index_passwords[tag])
        idx_meta["entries"].append(entry_meta)
        storage.update_index(library, tag, index_passwords[tag], idx_meta)

    # Update library manifest if new indexes were added
    if new_indexes:
        lib_meta["indexes"] = lib_meta.get("indexes", []) + new_indexes
        storage.update_library_meta(library, lib_password, lib_meta)

    console.print(f"[green]Entry saved.[/green] ID: {entry_id}")
    return lib_meta


# ── Browse flows ───────────────────────────────────────────────────────────────

def _browse_index_flow(library: str, lib_meta: dict):
    indexes = lib_meta.get("indexes", [])
    if not indexes:
        console.print("[yellow]No indexes yet. Write some entries first.[/yellow]")
        return

    for i, idx in enumerate(indexes, 1):
        console.print(f"  [{i}] @{idx}")
    choice = input("Select index: ").strip()
    try:
        tag = indexes[int(choice) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        return

    password = getpass.getpass(f"Index password for @{tag}: ")
    try:
        idx_meta = storage.open_index(library, tag, password)
    except WrongPassword:
        console.print("[red]Wrong password.[/red]")
        return

    entries = idx_meta.get("entries", [])
    if not entries:
        console.print("[yellow]No entries in this index.[/yellow]")
        return

    console.print("[dim]Filter by date? Leave blank to see all entries.[/dim]")
    date_from = input("From (YYYY-MM-DD) or blank: ").strip()
    date_to = input("To   (YYYY-MM-DD) or blank: ").strip()

    filtered = _filter_entries(entries, date_from, date_to)
    if not filtered:
        console.print("[yellow]No entries match that date range.[/yellow]")
        return

    _display_entries(filtered, tag)

    choice = input("\nOpen entry number (or blank to go back): ").strip()
    if not choice:
        return
    try:
        entry = filtered[int(choice) - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        return

    _open_entry_flow(library, entry)


def _open_entry_flow(library: str, entry: dict):
    password = getpass.getpass(f"Document password for {entry['id']}: ")
    try:
        content = storage.load_entry(library, entry["id"], password)
    except WrongPassword:
        console.print("[red]Wrong password.[/red]")
        return
    except FileNotFoundError:
        console.print("[red]Entry file not found.[/red]")
        return

    console.print(
        Panel(
            content,
            title=f"[cyan]{indexer.format_date(entry['date'])}[/cyan]  "
            f"[dim]{entry['word_count']} words[/dim]",
            border_style="dim",
        )
    )

    action = input("\n[e]dit  [b]ack: ").strip().lower()
    if action == "e":
        new_content = editor.open_editor(content)
        if new_content == content:
            console.print("[dim]No changes.[/dim]")
            return
        storage.save_entry(library, entry["id"], new_content, password)
        console.print("[green]Entry updated.[/green]")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _filter_entries(entries: list, date_from: str, date_to: str) -> list:
    result = []
    for e in entries:
        entry_date = e["date"][:10]
        if date_from and entry_date < date_from:
            continue
        if date_to and entry_date > date_to:
            continue
        result.append(e)
    return sorted(result, key=lambda x: x["date"], reverse=True)


def _display_entries(entries: list, tag: str):
    table = Table(title=f"@{tag}", box=box.SIMPLE)
    table.add_column("#", style="dim", width=4)
    table.add_column("Date", style="cyan", width=17)
    table.add_column("Words", style="yellow", width=6)
    table.add_column("Tags", style="green", width=22)
    table.add_column("Preview", style="white")

    for i, e in enumerate(entries, 1):
        tags_str = " ".join(f"@{t}" for t in e.get("tags", []))
        table.add_row(
            str(i),
            indexer.format_date(e["date"]),
            str(e["word_count"]),
            tags_str,
            e.get("preview", ""),
        )

    console.print(table)


if __name__ == "__main__":
    main()
