from pathlib import Path

import typer
from rich.console import Console

from demand_radar import db
from demand_radar.collector import collect_subreddit
from demand_radar.config import get_settings
from demand_radar.reports import generate_report

app = typer.Typer(help="Demand Radar local Reddit ETL")
console = Console()


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
