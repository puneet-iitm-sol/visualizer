from __future__ import annotations

import re
from pathlib import Path

# Filename patterns used by the official Prosperity round drops:
#   prices_round_1_day_0.csv
#   trades_round_1_day_0_nn.csv   (older format; kept here as a fallback)
#   trades_round_1_day_-1.csv
_PRICES_RE = re.compile(r"prices_round_(?P<round>-?\d+)_day_(?P<day>-?\d+)", re.IGNORECASE)
_TRADES_RE = re.compile(r"trades_round_(?P<round>-?\d+)_day_(?P<day>-?\d+)", re.IGNORECASE)


def classify_csv(name: str) -> tuple[str | None, int | None, int | None]:
    """Return (kind, round, day) if the filename matches a Prosperity pattern."""
    stem = Path(name).stem
    m = _PRICES_RE.search(stem)
    if m:
        return "prices", int(m["round"]), int(m["day"])
    m = _TRADES_RE.search(stem)
    if m:
        return "trades", int(m["round"]), int(m["day"])
    return None, None, None


def read_bytes(path: Path, *, max_bytes: int | None = None) -> bytes:
    data = path.read_bytes()
    if max_bytes is not None and len(data) > max_bytes:
        raise ValueError(f"file {path.name} exceeds {max_bytes} bytes")
    return data


def sniff_separator(sample: str, candidates: tuple[str, ...] = (";", ",", "\t", "|")) -> str:
    """Count candidate separators in the first non-empty line and return the winner."""
    first_line = next((ln for ln in sample.splitlines() if ln.strip()), "")
    best = candidates[0]
    best_count = -1
    for sep in candidates:
        count = first_line.count(sep)
        if count > best_count:
            best, best_count = sep, count
    return best


def decode_text(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
