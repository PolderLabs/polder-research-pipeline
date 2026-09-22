"""Canonical template registry.

Templates live under ``99-templates/`` in the repository root. There is no
parallel hard-coded inventory anywhere else: scripts, tests, and agents
must resolve a template through :func:`registry` or :class:`TemplateRegistry`.

A template name is the file stem with the trailing ``-template`` stripped.
``research-note-template.md`` -> ``research-note``; ``README.md`` is not a
template and is excluded. ``resolve(name)`` returns a :class:`Template` whose
``path`` and ``text`` come from the same canonical file the registry
enumerated.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .paths import REPO_ROOT


@dataclass(frozen=True)
class Template:
    """A single canonical template document."""

    name: str
    path: Path
    text: str


class TemplateRegistry:
    """A view over ``repo_root/99-templates``."""

    def __init__(self, repo_root: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
        self.templates_dir = self.repo_root / "99-templates"
        if not self.templates_dir.is_dir():
            raise FileNotFoundError(f"templates directory does not exist: {self.templates_dir}")

    def names(self) -> tuple[str, ...]:
        """Template names in deterministic filename order."""
        return tuple(self._iter_names())

    def __iter__(self) -> Iterator[Template]:
        for name in self._iter_names():
            yield self.resolve(name)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in set(self.names())

    def __len__(self) -> int:
        return len(self.names())

    def resolve(self, name: str) -> Template:
        """Return the canonical :class:`Template` for ``name``.

        Raises ``KeyError`` if the template name is unknown.
        """
        for template in self._iter_files():
            if template.name == name:
                return template
        raise KeyError(name)

    def _iter_names(self) -> Iterator[str]:
        for template in self._iter_files():
            yield template.name

    def _iter_files(self) -> Iterator[Template]:
        for path in sorted(self.templates_dir.glob("*-template.md")):
            yield Template(
                name=_template_name(path),
                path=path,
                text=path.read_text(encoding="utf-8"),
            )


def _template_name(path: Path) -> str:
    """Return the canonical template name for ``path``.

    ``research-note-template.md`` -> ``research-note``; non-template files
    such as ``README.md`` are not produced here because the glob pattern
    only matches ``*-template.md``.
    """
    stem = path.name.removesuffix(".md")
    if not stem.endswith("-template"):
        raise ValueError(f"not a template file: {path}")
    return stem[: -len("-template")]


def registry(repo_root: Path | str | None = None) -> TemplateRegistry:
    """Return the canonical template registry for ``repo_root``."""
    return TemplateRegistry(repo_root)


__all__ = ["Template", "TemplateRegistry", "registry"]
