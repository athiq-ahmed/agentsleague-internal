"""
demo_intake.py – Interactive demo for Block 1: Learner Intake & Profiling

Run:
    python demo_intake.py

Requires:
    .env file with AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY set.
    See .env for format (commented examples are included).
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

# ── make src/ importable without installing the package ──────────────────────
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich import box

from cert_prep.b0_intake_agent import run_intake_and_profiling
from cert_prep.models import DomainKnowledge, LearnerProfile, RawStudentInput

console = Console()

# ─── Colour map for domain knowledge levels ──────────────────────────────────
LEVEL_STYLE = {
    DomainKnowledge.UNKNOWN:  "bold red",
    DomainKnowledge.WEAK:     "bold yellow",
    DomainKnowledge.MODERATE: "bold cyan",
    DomainKnowledge.STRONG:   "bold green",
}

LEVEL_ICON = {
    DomainKnowledge.UNKNOWN:  "✗",
    DomainKnowledge.WEAK:     "~",
    DomainKnowledge.MODERATE: "◑",
    DomainKnowledge.STRONG:   "✓",
}


# ─── Display helpers ─────────────────────────────────────────────────────────

def _bar(score: float, width: int = 16) -> str:
    filled = round(score * width)
    return "[" + "█" * filled + "░" * (width - filled) + f"] {score:.0%}"


def show_profile(raw: RawStudentInput, profile: LearnerProfile) -> None:
    """Render the LearnerProfile in a rich multi-panel layout."""

    console.print()
    console.rule("[bold magenta]Block 1 Output — Learner Profile[/bold magenta]")
    console.print()

    # ── Summary card ─────────────────────────────────────────────────────────
    summary = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    summary.add_column("Key",   style="bold cyan",  no_wrap=True)
    summary.add_column("Value", style="white")
    summary.add_row("Student",          profile.student_name)
    summary.add_row("Exam target",      profile.exam_target)
    summary.add_row("Experience level", profile.experience_level.value.replace("_", " ").title())
    summary.add_row("Learning style",   profile.learning_style.value.replace("_", " ").title())
    summary.add_row("Study budget",
                    f"[bold]{profile.hours_per_week:.0f} h/wk × {profile.weeks_available} wks "
                    f"= [green]{profile.total_budget_hours:.0f} h total[/green][/bold]")
    existing = ", ".join(raw.existing_certs) if raw.existing_certs else "[dim]None[/dim]"
    summary.add_row("Existing certs",   existing)

    console.print(Panel(summary, title="[bold]Student Summary[/bold]", border_style="magenta"))

    # ── Domain knowledge table ────────────────────────────────────────────────
    dom_table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold white on dark_violet",
        padding=(0, 1),
    )
    dom_table.add_column("Domain",         style="white",      min_width=40)
    dom_table.add_column("Level",          justify="center",   min_width=10)
    dom_table.add_column("Confidence",     justify="left",     min_width=24)
    dom_table.add_column("Skip?",          justify="center",   min_width=6)
    dom_table.add_column("Notes",          style="dim white",  min_width=32)

    for dp in profile.domain_profiles:
        style = LEVEL_STYLE.get(dp.knowledge_level, "white")
        icon  = LEVEL_ICON.get(dp.knowledge_level, "?")
        skip  = "[bold green]Yes[/bold green]" if dp.skip_recommended else "[dim]No[/dim]"
        dom_table.add_row(
            dp.domain_name,
            f"[{style}]{icon} {dp.knowledge_level.value.upper()}[/{style}]",
            _bar(dp.confidence_score),
            skip,
            dp.notes,
        )

    console.print(Panel(dom_table, title="[bold]Domain Knowledge Map[/bold]", border_style="blue"))

    # ── Risk + skip callout ───────────────────────────────────────────────────
    risks = ", ".join(profile.risk_domains) if profile.risk_domains else "[dim]None identified[/dim]"
    skips = (
        ", ".join(profile.modules_to_skip) if profile.modules_to_skip
        else "[dim]None — full syllabus required[/dim]"
    )
    callout = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    callout.add_column("Key",   style="bold yellow", no_wrap=True)
    callout.add_column("Value", style="white")
    callout.add_row("[bold red]⚠ Risk domains[/bold red]",  risks)
    callout.add_row("[bold green]⏭ Skip candidates[/bold green]", skips)
    console.print(Panel(callout, title="[bold]Routing Flags[/bold]", border_style="yellow"))

    # ── Analogy map (only if populated) ──────────────────────────────────────
    if profile.analogy_map:
        am = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", padding=(0, 1))
        am.add_column("Your existing skill",    style="cyan")
        am.add_column("→ Azure AI equivalent",  style="green")
        for skill, equiv in profile.analogy_map.items():
            am.add_row(skill, equiv)
        console.print(Panel(am, title="[bold]Skill Analogy Map[/bold]", border_style="cyan"))

    # ── Recommended approach ──────────────────────────────────────────────────
    console.print(Panel(
        f"[italic]{profile.recommended_approach}[/italic]\n\n"
        f"[dim]{profile.engagement_notes}[/dim]",
        title="[bold]Personalisation Notes → Downstream Agents[/bold]",
        border_style="green",
    ))

    console.print()
    console.rule("[bold green]Block 1 complete — profile ready for Learning Path Planner[/bold green]")
    console.print()


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    console.print()
    console.print(Panel(
        "[bold]Microsoft Agents League — Certification Prep[/bold]\n"
        "[dim]Multi-Agent System  •  Block 1: Learner Intake & Profiling[/dim]",
        style="on dark_violet",
        expand=False,
    ))

    try:
        raw, profile = run_intake_and_profiling()
        show_profile(raw, profile)

    except EnvironmentError as e:
        console.print(f"\n[bold red]Configuration error:[/bold red] {e}")
        console.print("[dim]Fill in AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY in .env and retry.[/dim]")
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(0)

    except Exception:
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
