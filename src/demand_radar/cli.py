from pathlib import Path

import typer
from rich.console import Console

from demand_radar import db
from demand_radar.collector import collect_subreddit, collect_watchlist
from demand_radar.config import get_settings
from demand_radar.reports import generate_report

app = typer.Typer(help="Demand Radar local Reddit ETL")
console = Console()


def _parse_since_days(value: str | None) -> int | None:
    """Accept '7d', '14d', or a bare integer-day count. None disables the filter."""
    if value is None:
        return None
    stripped = value.strip().lower()
    if not stripped:
        return None
    if stripped.endswith("d"):
        stripped = stripped[:-1]
    return int(stripped)


@app.command("init-db")
def init_db() -> None:
    """Create local SQLite database tables."""
    settings = get_settings()
    db.init_db(settings.database_path)
    console.print(f"Database initialized: {settings.database_path}")


@app.command("collect")
def collect(
    subreddit: str = typer.Option(..., help="Subreddit name without r/"),
    limit: int = typer.Option(100, help="Number of new posts to fetch"),
    comment_limit: int = typer.Option(50, help="Top-level comments to fetch per relevant post"),
    sleep_seconds: float = typer.Option(1.0, help="Polite sleep between comment fetches"),
) -> None:
    """Collect posts and selected comments from one subreddit."""
    settings = get_settings()
    db.init_db(settings.database_path)
    result = collect_subreddit(
        settings=settings,
        subreddit_name=subreddit,
        limit=limit,
        comment_limit=comment_limit,
        sleep_seconds=sleep_seconds,
    )
    console.print(result)


@app.command("collect-watchlist")
def collect_watchlist_cmd(
    since: str = typer.Option(
        "7d", "--since", help="Only keep posts newer than this window (e.g. '7d')."
    ),
    limit: int = typer.Option(50, "--limit", help="Max posts per subreddit."),
    watchlist: str = typer.Option(
        "data/watchlist.csv",
        "--watchlist",
        help="Path to watchlist CSV (subreddit column required).",
    ),
    sleep_seconds: float = typer.Option(
        2.0, "--sleep-seconds", help="Polite sleep between subreddits (>= 2.0)."
    ),
) -> None:
    """Loop the watchlist, politely fetch new posts per subreddit, dedupe, extract signals."""
    settings = get_settings()
    result = collect_watchlist(
        settings=settings,
        watchlist_path=Path(watchlist),
        per_sub_limit=limit,
        since_days=_parse_since_days(since),
        sleep_between_subs=sleep_seconds,
    )
    console.print(result)


@app.command("report")
def report(days: int = typer.Option(7, help="Report window in days")) -> None:
    """Generate Markdown and CSV reports."""
    settings = get_settings()
    path = generate_report(settings, days=days)
    console.print(f"Report written: {path}")


@app.command("where")
def where() -> None:
    """Print local paths."""
    settings = get_settings()
    console.print(f"Database: {Path(settings.database_path).resolve()}")
    console.print(f"Reports: {Path(settings.reports_dir).resolve()}")
