"""VeriFact CLI — `verifact analyze <url|text>`, `verifact serve`."""

from __future__ import annotations

import asyncio
import json as jsonlib
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__, pipeline
from .models import CredibilityReport, SignalStatus

app = typer.Typer(
    name="verifact",
    help="Verify the credibility of news articles, posts and images.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

_VERDICT_STYLE = {
    "high_credibility": ("green", "✅"),
    "moderate_credibility": ("yellow", "🟡"),
    "low_credibility": ("dark_orange", "⚠️ "),
    "very_low_credibility": ("red", "🚨"),
    "insufficient_evidence": ("grey62", "❔"),
}

_IMPACT_ICON = {"positive": "[green]+[/]", "negative": "[red]−[/]", "neutral": "·", "informational": "[cyan]i[/]"}


def _render(report: CredibilityReport) -> None:
    color, icon = _VERDICT_STYLE[report.verdict.value]
    score_txt = f"{report.score}/100" if report.score is not None else "—"
    console.print(
        Panel(
            f"[bold {color}]{icon} {report.verdict_label}[/]  "
            f"[bold]{score_txt}[/]  (confidence {report.confidence:.0%})\n\n{report.summary}",
            title=f"VeriFact v{__version__}",
            subtitle=report.meta.url or report.input_type,
        )
    )
    table = Table(show_lines=False, pad_edge=False, box=None)
    table.add_column("Signal", style="bold", min_width=22)
    table.add_column("Score", justify="right", min_width=6)
    table.add_column("Details")
    for s in report.signals:
        if s.status == SignalStatus.SKIPPED:
            table.add_row(f"[dim]{s.title}[/]", "[dim]skip[/]", f"[dim]{s.summary}[/]")
            continue
        if s.status == SignalStatus.ERROR:
            table.add_row(f"[red]{s.title}[/]", "[red]err[/]", f"[red]{s.summary}[/]")
            continue
        score = f"{s.score:.0f}" if s.score is not None else "—"
        lines = [s.summary] + [
            f"  {_IMPACT_ICON[f.impact]} {f.label}" + (f" — {f.detail}" if f.detail else "")
            for f in s.findings[:6]
        ]
        table.add_row(s.title, score, "\n".join(lines))
    console.print(table)
    console.print(f"\n[dim]{report.disclaimer}[/]")


@app.command()
def analyze(
    target: str = typer.Argument(..., help="URL to analyze, raw text, or path to an image"),
    json: bool = typer.Option(False, "--json", help="Emit the full report as JSON"),
    caption: str = typer.Option("", help="Caption/claim accompanying an image"),
) -> None:
    """Analyze a URL, a block of text, or an image file."""
    path = Path(target)
    if path.exists() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tiff"}:
        report = asyncio.run(pipeline.analyze_image(str(path), caption))
    elif target.startswith(("http://", "https://")):
        report = asyncio.run(pipeline.analyze_url(target))
    else:
        report = asyncio.run(pipeline.analyze_text(target))

    if json:
        console.print_json(jsonlib.dumps(report.model_dump(mode="json")))
    else:
        _render(report)


@app.command()
def serve(
    host: str = typer.Option(None, help="Bind host (default from VERIFACT_HOST or 127.0.0.1)"),
    port: int = typer.Option(None, help="Bind port (default from VERIFACT_PORT or 8000)"),
) -> None:
    """Start the VeriFact API + web UI."""
    import uvicorn

    from .config import get_settings

    settings = get_settings()
    uvicorn.run(
        "verifact.api.server:app",
        host=host or settings.host,
        port=port or settings.port,
    )


@app.command()
def version() -> None:
    """Print version."""
    console.print(f"verifact {__version__}")


if __name__ == "__main__":
    app()
