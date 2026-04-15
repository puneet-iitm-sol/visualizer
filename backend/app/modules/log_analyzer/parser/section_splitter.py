"""Pass 1 — detect and split a Prosperity log into its constituent sections.

Prosperity 4 ships logs as a single JSON object:
    {
        "submissionId": "...",
        "activitiesLog": "day;timestamp;product;...\n0;0;KELP;...",
        "logs": [{"timestamp":0, "sandboxLog":"", "lambdaLog":"..."}, ...],
        "tradeHistory": [{"timestamp":100, "buyer":"...", ...}, ...]
    }

Older rounds (1–3) used a multi-section plain-text format:
    Sandbox logs:
    {"timestamp":0, ...}
    Activities log:
    day;timestamp;...
    Trade History:
    [...]

We detect which format the file is in and normalise everything into the same
`Section` data class so the rest of the pipeline is format-agnostic.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum


class SectionKind(str, Enum):
    SANDBOX = "sandbox"
    ACTIVITIES = "activities"
    TRADE_HISTORY = "trade_history"
    UNKNOWN = "unknown"


@dataclass
class Section:
    kind: SectionKind
    start_line: int      # 0-based (set to 0 for JSON-derived sections)
    end_line: int
    header: str
    text: str            # raw content for text format; JSON string for JSON format
    raw: object = None   # pre-parsed Python object when available (list / dict)


# ──────────────────────────────────────────────
# JSON format (Prosperity 4)
# ──────────────────────────────────────────────
def _try_parse_json(text: str) -> list[Section] | None:
    """Return sections if `text` is a Prosperity 4 JSON log, else None."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return None
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    # Must have at least one of the known Prosperity 4 keys.
    if not any(k in obj for k in ("activitiesLog", "logs", "tradeHistory")):
        return None

    sections: list[Section] = []

    if "activitiesLog" in obj:
        sections.append(Section(
            kind=SectionKind.ACTIVITIES,
            start_line=0, end_line=0,
            header="activitiesLog (JSON)",
            text=str(obj["activitiesLog"]),
            raw=obj["activitiesLog"],
        ))

    if "logs" in obj and isinstance(obj["logs"], list):
        sections.append(Section(
            kind=SectionKind.SANDBOX,
            start_line=0, end_line=0,
            header="logs (JSON)",
            text="",          # handled via .raw
            raw=obj["logs"],
        ))

    if "tradeHistory" in obj and isinstance(obj["tradeHistory"], list):
        sections.append(Section(
            kind=SectionKind.TRADE_HISTORY,
            start_line=0, end_line=0,
            header="tradeHistory (JSON)",
            text="",          # handled via .raw
            raw=obj["tradeHistory"],
        ))

    return sections if sections else None


# ──────────────────────────────────────────────
# Text format (Prosperity 1–3 / manual logs)
# ──────────────────────────────────────────────
_HEADER_PATTERNS: tuple[tuple[re.Pattern[str], SectionKind], ...] = (
    (re.compile(r"^\s*trade\s*history\s*:?\s*$", re.IGNORECASE), SectionKind.TRADE_HISTORY),
    (re.compile(r"^\s*activities?\s*(log)?\s*:?\s*$", re.IGNORECASE), SectionKind.ACTIVITIES),
    (re.compile(r"^\s*sandbox\s*(logs?)?\s*:?\s*$", re.IGNORECASE), SectionKind.SANDBOX),
)


def _classify_header(line: str) -> SectionKind | None:
    if not line.strip():
        return None
    for pat, kind in _HEADER_PATTERNS:
        if pat.match(line):
            return kind
    return None


def _parse_text(text: str) -> list[Section]:
    lines = text.splitlines()
    boundaries: list[tuple[int, SectionKind, str]] = []

    for idx, line in enumerate(lines):
        kind = _classify_header(line)
        if kind is not None:
            boundaries.append((idx, kind, line))

    if not boundaries:
        return [Section(
            kind=SectionKind.UNKNOWN,
            start_line=0, end_line=len(lines),
            header="", text=text,
        )]

    sections: list[Section] = []
    first_idx = boundaries[0][0]
    if first_idx > 0 and any(ln.strip() for ln in lines[:first_idx]):
        sections.append(Section(
            kind=SectionKind.UNKNOWN, start_line=0, end_line=first_idx,
            header="", text="\n".join(lines[:first_idx]),
        ))

    for i, (idx, kind, header) in enumerate(boundaries):
        start = idx + 1
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(lines)
        body = "\n".join(lines[start:end]).strip("\n")
        sections.append(Section(kind=kind, start_line=start, end_line=end, header=header, text=body))

    return sections


# ──────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────
def split_sections(text: str) -> list[Section]:
    """Auto-detect format and return normalised Section list."""
    json_sections = _try_parse_json(text)
    if json_sections is not None:
        return json_sections
    return _parse_text(text)
