from dataclasses import dataclass
from typing import Callable

from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class PageDefinition:
    key: str
    title: str
    nav_label: str
    section: str
    factory: Callable[[], QWidget]
