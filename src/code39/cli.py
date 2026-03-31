"""CLI entrypoint for code-39."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from . import __version__
from .card_renderer import interleave_front_verso, render_batch_cards_pdf, render_batch_cards_pngs
from .card_template import CardTemplate, load_card_template
from .pdf import derive_png_output_dir, render_batch_pdf, render_batch_pngs
from .registry import RegistryError, RegistryStore
from .service import build_batch_plan, find_duplicates, next_available_reference

app = typer.Typer(help="Generate print-ready Code 39 batches for Atlântico Gastrobar.")
console = Console()

DEFAULT_OUTPUT = Path("output/code-39-batch.pdf")
DEFAULT_REGISTRY = Path("data/registry.json")
DEFAULT_HISTORY = Path("data/batches.jsonl")


def main() -> None:
    """Run the CLI application."""
    app()


def _exit_for_storage_error(error: RegistryError) -> typer.Exit:
    """Translate persistence failures into a stable CLI exit code."""
    console.print(f"[red]Storage error:[/red] {error}")
    return typer.Exit(3)


@app.command()
def generate(
    start: int = typer.Option(1, help="First numeric reference to include."),
    end: int = typer.Option(500, help="Last numeric reference to include."),
    limit: int | None = typer.Option(None, help="Optional cap for quick validation batches."),
    reference: str | None = typer.Option(None, help="Generate a single reference such as ATL125."),
    output: Path = typer.Option(DEFAULT_OUTPUT, help="PDF output path."),
    png_dir: Path | None = typer.Option(None, help="Directory for individual PNG files."),
    registry: Path = typer.Option(DEFAULT_REGISTRY, help="Registry JSON path."),
    history: Path = typer.Option(DEFAULT_HISTORY, help="Append-only batch history path."),
    png: bool = typer.Option(True, "--png/--no-png", help="Generate one PNG file per reference."),
    force: bool = typer.Option(False, "--force", help="Allow regeneration of previously issued references."),
    mode: str = typer.Option("labels", "--mode", help="Rendering mode: labels (A4 grid) or cards (template-based)."),
    template: Path | None = typer.Option(None, "--template", help="Card template JSON (required when --mode cards)."),
    front_pdf: Path | None = typer.Option(None, "--front-pdf", help="PDF da frente para intercalar com o verso (modo cards)."),
    front_pages_per_verso: int = typer.Option(2, "--front-pages-per-verso", help="Páginas da frente antes de cada verso (ex: 2 = pula 2, joga verso)."),
) -> None:
    """Generate a PDF batch and persist the issued references."""
    try:
        plan = build_batch_plan(start=start, end=end, limit=limit, reference=reference)
    except ValueError as error:
        console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(1) from error

    normalized_mode = mode.strip().lower()

    store = RegistryStore(registry, history)
    resolved_png_dir = png_dir or derive_png_output_dir(output)
    total_render_steps = plan.quantity * (2 if png else 1)
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )
    with progress:
        task = progress.add_task("Rendering assets", total=total_render_steps)
        try:
            with store.generation_lock():
                duplicates = find_duplicates(plan.references, store.get_generated_references())
                if duplicates and not force:
                    console.print("[red]Generation blocked.[/red] The following references already exist:")
                    for duplicate in duplicates[:10]:
                        console.print(f"  - {duplicate}")
                    if len(duplicates) > 10:
                        console.print(f"  ... and {len(duplicates) - 10} more")
                    console.print("Use [bold]--force[/bold] only when regeneration is intentional.")
                    raise typer.Exit(2)

                console.print()
                console.print(
                    f"[bold cyan]Generating {plan.quantity} reference(s)[/bold cyan] "
                    f"from [bold]{plan.first_reference}[/bold] to [bold]{plan.last_reference}[/bold]"
                )

                if normalized_mode == "labels":
                    render_batch_pdf(
                        plan.references,
                        output,
                        progress_callback=lambda reference: progress.update(
                            task,
                            description=f"Rendering PDF {reference}",
                            advance=1,
                        ),
                    )
                    if png:
                        render_batch_pngs(
                            plan.references,
                            resolved_png_dir,
                            progress_callback=lambda reference: progress.update(
                                task,
                                description=f"Rendering PNG {reference}",
                                advance=1,
                            ),
                        )
                elif normalized_mode == "cards":
                    if template is None:
                        console.print(
                            "[red]Missing template.[/red] Provide --template when --mode cards."
                        )
                        raise typer.Exit(4)
                    card_template: CardTemplate = load_card_template(template)

                    verso_output = output
                    if front_pdf is not None:
                        if not front_pdf.exists():
                            console.print(f"[red]Front PDF not found:[/red] {front_pdf}")
                            raise typer.Exit(5)
                        verso_output = output.with_name(f"{output.stem}-verso-only.pdf")

                    render_batch_cards_pdf(
                        plan.references,
                        verso_output,
                        card_template,
                        progress_callback=lambda reference: progress.update(
                            task,
                            description=f"Rendering Cards PDF {reference}",
                            advance=1,
                        ),
                    )

                    if front_pdf is not None:
                        interleave_front_verso(
                            front_pdf,
                            verso_output,
                            output,
                            front_pages_per_verso=front_pages_per_verso,
                        )
                        verso_output.unlink(missing_ok=True)

                    if png:
                        render_batch_cards_pngs(
                            plan.references,
                            resolved_png_dir,
                            card_template,
                            progress_callback=lambda reference: progress.update(
                                task,
                                description=f"Rendering Card PNG {reference}",
                                advance=1,
                            ),
                        )
                else:
                    console.print(f"[red]Unknown mode:[/red] {mode}. Use 'labels' or 'cards'.")
                    raise typer.Exit(4)

                store.register_batch(plan.references, output_file=str(output), force=force)
        except RegistryError as error:
            raise _exit_for_storage_error(error) from error

    table = Table(title="Batch summary")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Output", str(output))
    table.add_row("Quantity", str(plan.quantity))
    table.add_row("First", plan.first_reference)
    table.add_row("Last", plan.last_reference)
    table.add_row("Mode", normalized_mode)
    table.add_row("PNG output", str(resolved_png_dir) if png else "disabled")
    table.add_row("Force", "yes" if force else "no")
    if normalized_mode == "cards" and front_pdf is not None:
        table.add_row("Front PDF", str(front_pdf))
    console.print(table)


@app.command()
def status(
    registry: Path = typer.Option(DEFAULT_REGISTRY, help="Registry JSON path."),
    history: Path = typer.Option(DEFAULT_HISTORY, help="Append-only batch history path."),
) -> None:
    """Show current registry information."""
    store = RegistryStore(registry, history)
    try:
        generated = sorted(store.get_generated_references())
        batches = store.read_history()
    except RegistryError as error:
        raise _exit_for_storage_error(error) from error

    table = Table(title="Registry status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Generated references", str(len(generated)))
    table.add_row("Batches logged", str(len(batches)))
    table.add_row("Last reference", generated[-1] if generated else "-")
    table.add_row("Next available", next_available_reference(set(generated)) or "all issued")
    table.add_row("Registry path", str(registry))
    table.add_row("History path", str(history))
    console.print(table)


@app.command()
def history(
    registry: Path = typer.Option(DEFAULT_REGISTRY, help="Registry JSON path."),
    history: Path = typer.Option(DEFAULT_HISTORY, help="Append-only batch history path."),
    limit: int = typer.Option(20, help="Maximum number of records to display."),
) -> None:
    """Print the append-only history of generated batches."""
    store = RegistryStore(registry, history)
    try:
        records = store.read_history()
    except RegistryError as error:
        raise _exit_for_storage_error(error) from error
    if not records:
        console.print("[yellow]No batches generated yet.[/yellow]")
        return

    table = Table(title="Batch history")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Range")
    table.add_column("Qty", justify="right")
    table.add_column("Force", justify="center")
    table.add_column("Output")
    for record in records[-limit:]:
        table.add_row(
            record["timestamp"],
            f'{record["first_reference"]} -> {record["last_reference"]}',
            str(record["quantity"]),
            "yes" if record["force"] else "no",
            record["output_file"],
        )
    console.print(table)


@app.command()
def version() -> None:
    """Print the current CLI version."""
    console.print(f"code-39 {__version__}")


if __name__ == "__main__":
    main()
