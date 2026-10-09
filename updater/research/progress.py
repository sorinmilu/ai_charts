"""Pretty step progress for the updater CLI."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TextIO


@dataclass
class Progress:
    stream: TextIO = field(default_factory=lambda: sys.stdout)
    enabled: bool = True
    _active: str | None = field(default=None, init=False, repr=False)

    def step(self, label: str) -> None:
        """Start a step (shown as in-progress)."""
        self._finish_open()
        self._active = label
        self._write(f"  · {label}...")

    def ok(self, detail: str | None = None) -> None:
        """Mark the current step done."""
        label = self._active or "Done"
        self._active = None
        text = f"  ✓ {label}" if not detail else f"  ✓ {label} — {detail}"
        self._write(text)

    def fail(self, detail: str | None = None) -> None:
        """Mark the current step failed."""
        label = self._active or "Failed"
        self._active = None
        text = f"  ✗ {label}" if not detail else f"  ✗ {label} — {detail}"
        self._write(text)

    def note(self, text: str) -> None:
        """Print a note under the current step (does not close it)."""
        self._write(f"    {text}")

    def blank(self) -> None:
        if self.enabled:
            print(file=self.stream, flush=True)

    def _finish_open(self) -> None:
        if self._active is not None:
            # Step replaced without ok/fail — close quietly as done.
            label = self._active
            self._active = None
            self._write(f"  ✓ {label}")

    def _write(self, line: str) -> None:
        if not self.enabled:
            return
        print(line, file=self.stream, flush=True)


NO_PROGRESS = Progress(enabled=False)
