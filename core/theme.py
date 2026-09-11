from pathlib import Path


def load_stylesheet(base_dir: Path, filename: str = "dark_v3.qss") -> str:
    style_path = base_dir / "styles" / filename
    return style_path.read_text(encoding="utf-8")
