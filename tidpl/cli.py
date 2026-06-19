import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from typing_extensions import Annotated

from tidpl.auth import make_api, load_auth
from tidpl.playlist import export_daily, make_deli_mix_from_file

app = typer.Typer(name="tidpl", no_args_is_help=True)
console = Console()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MIXES_FILE = DATA_DIR / "mixes.txt"
BLOCKLIST_FILE = DATA_DIR / "artist_blocklist.txt"
ALL_TRACKS_FILE = DATA_DIR / "all_tracks.txt"
DAILY_FILE = DATA_DIR / "DailyTidal.txt"
HISTORY_FILE = DATA_DIR / "daily_history.json"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.callback()
def callback(
    ctx: typer.Context,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    _setup_logging(verbose)
    ctx.ensure_object(dict)


@app.command()
def export(
    mixes: Annotated[
        Path, typer.Option("-i", "--input", help="File with mix/playlist URLs.")
    ] = MIXES_FILE,
    blocklist: Annotated[
        Path, typer.Option("-b", "--blocklist", help="Artist blocklist file.")
    ] = BLOCKLIST_FILE,
    output_all: Annotated[
        Path, typer.Option("-o", "--output", help="Output all-tracks file.")
    ] = ALL_TRACKS_FILE,
    output_daily: Annotated[
        Path, typer.Option("-d", "--daily", help="Output daily selection file.")
    ] = DAILY_FILE,
    history: Annotated[
        Path, typer.Option("--history", help="History JSON for dedup.")
    ] = HISTORY_FILE,
    count: Annotated[
        int, typer.Option("-n", "--count", help="Number of tracks in daily selection.")
    ] = 100,
    history_days: Annotated[
        int, typer.Option("--history-days", help="Days to exclude a selected track.")
    ] = 3,
):
    """Fetch tracks from mixes, deduplicate, filter, and pick a random daily selection."""
    auth_data = load_auth()
    api = make_api(auth_data)
    picked = export_daily(
        api=api,
        mixes_file=mixes,
        blocklist_file=blocklist,
        output_all=output_all,
        output_daily=output_daily,
        history_file=history,
        count=count,
        history_days=history_days,
    )
    console.print(
        f"[bold green]Exported {len(picked)} tracks to {output_daily}[/bold green]"
    )


@app.command()
def push(
    input: Annotated[
        Path,
        typer.Argument(
            help="Text file with 'artist - title' lines (one per line).",
            exists=True,
        ),
    ] = DAILY_FILE,
    name: Annotated[
        str, typer.Option("-n", "--name", help="Playlist name in Tidal.")
    ] = "Deli Mix",
    description: Annotated[
        str, typer.Option("-d", "--description", help="Playlist description.")
    ] = "Daily Tidal selection \u2014 created by tidpl",
):
    """Search tracks from a text file and push them into a Tidal playlist."""
    auth_data = load_auth()
    api = make_api(auth_data)

    console.print(f"[cyan]Searching {input} on Tidal...[/cyan]")
    uuid = make_deli_mix_from_file(
        api=api,
        track_file=input,
        playlist_title=name,
        playlist_description=description,
    )
    url = f"https://tidal.com/browse/playlist/{uuid}"
    console.print(f"[bold green]Playlist '{name}' created/updated: {url}[/bold green]")


@app.command()
def run(
    mixes: Annotated[
        Path, typer.Option("-i", "--input", help="File with mix/playlist URLs.")
    ] = MIXES_FILE,
    blocklist: Annotated[
        Path, typer.Option("-b", "--blocklist", help="Artist blocklist file.")
    ] = BLOCKLIST_FILE,
    output_all: Annotated[
        Path, typer.Option("-o", "--output", help="Output all-tracks file.")
    ] = ALL_TRACKS_FILE,
    output_daily: Annotated[
        Path, typer.Option("-d", "--daily", help="Output daily selection file.")
    ] = DAILY_FILE,
    history: Annotated[
        Path, typer.Option("--history", help="History JSON for dedup.")
    ] = HISTORY_FILE,
    count: Annotated[
        int, typer.Option("-n", "--count", help="Number of tracks in daily selection.")
    ] = 100,
    history_days: Annotated[
        int, typer.Option("--history-days", help="Days to exclude a selected track.")
    ] = 3,
    playlist_name: Annotated[
        str, typer.Option("--name", help="Playlist name in Tidal.")
    ] = "Deli Mix",
    playlist_desc: Annotated[
        str, typer.Option("--desc", help="Playlist description.")
    ] = "Daily Tidal selection \u2014 created by tidpl",
):
    """Full pipeline: export daily selection + push to Tidal playlist."""
    auth_data = load_auth()
    api = make_api(auth_data)

    console.print("[cyan]Step 1: Exporting daily selection from mixes...[/cyan]")
    picked = export_daily(
        api=api,
        mixes_file=mixes,
        blocklist_file=blocklist,
        output_all=output_all,
        output_daily=output_daily,
        history_file=history,
        count=count,
        history_days=history_days,
    )
    console.print(f"[green]  {len(picked)} tracks selected[/green]")

    console.print("[cyan]Step 2: Pushing to Tidal playlist...[/cyan]")
    uuid = make_deli_mix_from_file(
        api=api,
        track_file=output_daily,
        playlist_title=playlist_name,
        playlist_description=playlist_desc,
    )
    url = f"https://tidal.com/browse/playlist/{uuid}"
    console.print(f"[bold green]Done! Playlist: {url}[/bold green]")


if __name__ == "__main__":
    app()
