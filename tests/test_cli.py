from pathlib import Path

from typer.testing import CliRunner

from code39 import __version__
from code39.cli import app


runner = CliRunner()


def test_generate_command_creates_registry_and_history(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    png_dir = tmp_path / "out-png"
    registry = tmp_path / "registry.json"
    history = tmp_path / "history.jsonl"

    result = runner.invoke(
        app,
        [
            "generate",
            "--limit",
            "2",
            "--output",
            str(output),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    assert png_dir.exists()
    assert (png_dir / "ATL001.png").exists()
    assert (png_dir / "ATL002.png").exists()
    assert registry.exists()
    assert history.exists()


def test_generate_command_blocks_duplicates_without_force(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    registry = tmp_path / "registry.json"
    history = tmp_path / "history.jsonl"

    first = runner.invoke(
        app,
        [
            "generate",
            "--reference",
            "ATL001",
            "--output",
            str(output),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )
    second = runner.invoke(
        app,
        [
            "generate",
            "--reference",
            "ATL001",
            "--output",
            str(output),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )

    assert first.exit_code == 0
    assert second.exit_code == 2
    assert "Generation blocked" in second.stdout


def test_generate_command_allows_duplicates_with_force(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    png_dir = tmp_path / "out-png"
    registry = tmp_path / "registry.json"
    history = tmp_path / "history.jsonl"

    first = runner.invoke(
        app,
        [
            "generate",
            "--reference",
            "ATL001",
            "--output",
            str(output),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )
    second = runner.invoke(
        app,
        [
            "generate",
            "--reference",
            "ATL001",
            "--force",
            "--output",
            str(output),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert png_dir.exists()
    assert "Force" in second.stdout
    assert "yes" in second.stdout


def test_generate_command_can_disable_png_output(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    registry = tmp_path / "registry.json"
    history = tmp_path / "history.jsonl"

    result = runner.invoke(
        app,
        [
            "generate",
            "--limit",
            "2",
            "--no-png",
            "--output",
            str(output),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    assert not (tmp_path / "out-png").exists()
    assert "disabled" in result.stdout


def test_generate_command_rejects_invalid_limit(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "generate",
            "--limit",
            "0",
            "--output",
            str(tmp_path / "out.pdf"),
            "--registry",
            str(tmp_path / "registry.json"),
            "--history",
            str(tmp_path / "history.jsonl"),
        ],
    )

    assert result.exit_code == 1
    assert "Limit must be greater than zero" in result.stdout


def test_generate_command_supports_cards_mode(tmp_path: Path) -> None:
    output = tmp_path / "cards.pdf"
    png_dir = tmp_path / "cards-png"
    registry = tmp_path / "registry.json"
    history = tmp_path / "history.jsonl"

    result = runner.invoke(
        app,
        [
            "generate",
            "--mode",
            "cards",
            "--template",
            "tests/fixtures/card_template_stub.json",
            "--limit",
            "1",
            "--output",
            str(output),
            "--png-dir",
            str(png_dir),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    assert (png_dir / "ATL001.png").exists()


def test_status_command_reports_registry_metrics(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    registry = tmp_path / "registry.json"
    history = tmp_path / "history.jsonl"

    generate = runner.invoke(
        app,
        [
            "generate",
            "--limit",
            "2",
            "--output",
            str(output),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )
    result = runner.invoke(
        app,
        [
            "status",
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )

    assert generate.exit_code == 0
    assert result.exit_code == 0
    assert "Generated references" in result.stdout
    assert "2" in result.stdout
    assert "ATL003" in result.stdout


def test_history_command_lists_batches(tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    registry = tmp_path / "registry.json"
    history = tmp_path / "history.jsonl"

    generate = runner.invoke(
        app,
        [
            "generate",
            "--limit",
            "2",
            "--output",
            str(output),
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )
    result = runner.invoke(
        app,
        [
            "history",
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )

    assert generate.exit_code == 0
    assert result.exit_code == 0
    assert "Batch history" in result.stdout
    assert "ATL001 -> ATL002" in result.stdout


def test_version_command_prints_package_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert f"code-39 {__version__}" in result.stdout


def test_status_command_reports_corrupted_registry(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    history = tmp_path / "history.jsonl"
    registry.write_text("{invalid", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "status",
            "--registry",
            str(registry),
            "--history",
            str(history),
        ],
    )

    assert result.exit_code == 3
    assert "Storage error" in result.stdout
