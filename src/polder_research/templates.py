"""Canonical template registry.

Templates live under ``knowledge-base/99-templates/``. The :class:`TemplateRegistry`
resolves against :data:`.paths.VAULT_ROOT` (or an explicit vault root) so that
all callers — scripts, tests, and agents — share the same lookup.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .paths import VAULT_ROOT


@dataclass(frozen=True)
class Template:
    """A single canonical template document."""

    name: str
    path: Path
    text: str


class TemplateRegistry:
    """A view over ``VAULT_ROOT/99-templates``."""

    def __init__(self, repo_root: Path | str | None = None) -> None:
        # Accept a repo root or a vault root. If the caller passes a vault root
        # (identified by the ``knowledge-base`` tail), use it directly;
        # otherwise prepend ``knowledge-base``.
        if repo_root is None:
            vault: Path = VAULT_ROOT
        else:
            base = Path(repo_root)
            vault = base if base.name == "knowledge-base" else base / "knowledge-base"
        self.repo_root = vault
        self.templates_dir = vault / "99-templates"
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
