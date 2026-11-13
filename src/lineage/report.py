"""Markdown, JSON, and a self-contained HTML viewer."""

from __future__ import annotations

import html
import json
from pathlib import Path

from lineage import __version__
from lineage.models import DISCLAIMER, HOW_TO_READ, Evidence, Report, SignalResult

_CSS = """
:root {
  --bg: #efe8da;
  --paper: #fbf7ef;
  --ink: #1d1a16;
  --muted: #5f584e;
  --line: #ddd4c4;
  --accent: #1e4a3c;
  --accent-2: #1f3f5b;
  --low: #6f685e;
  --modest: #8a5424;
  --substantial: #1f3f5b;
  --high: #1e4a3c;
  --insufficient: #6f685e;
  --unavailable: #6f685e;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: Palatino, "Palatino Linotype", "Iowan Old Style", Georgia, serif;
  line-height: 1.5;
}
header.top, main { width: min(1120px, calc(100% - 32px)); margin: 0 auto; }
header.top { padding: 28px 0 8px; }
h1 { font-size: 2.1rem; font-weight: 600; letter-spacing: -0.02em; margin: 0 0 4px; }
.sub { color: var(--muted); margin: 0 0 16px; }
.disclaimer, .howto {
  background: var(--paper);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  padding: 12px 16px;
  margin: 12px 0 20px;
}
.disclaimer strong { font-family: "Segoe UI", Helvetica, sans-serif; font-size: 0.78rem; letter-spacing: 0.08em; }
nav.toc {
  display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 8px 0 18px;
  font-family: "Segoe UI", Helvetica, sans-serif; font-size: 0.92rem;
}
nav.toc a { color: var(--accent-2); }
.meta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 18px; }
.card, .signal, .region {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 16px;
}
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 10px 0 22px; }
.card h3, .signal h2 { margin: 0 0 6px; font-size: 1.05rem; }
.band {
  font-family: "Segoe UI", Helvetica, sans-serif; font-size: 0.75rem;
  letter-spacing: 0.06em; text-transform: uppercase;
}
.band.low, .band.insufficient, .band.unavailable { color: var(--low); }
.band.modest { color: var(--modest); }
.band.substantial { color: var(--substantial); }
.band.high { color: var(--high); }
.bar { height: 8px; background: #e6dece; border-radius: 99px; overflow: hidden; margin: 8px 0; }
.bar span { display: block; height: 100%; background: var(--accent); }
.score { font-variant-numeric: tabular-nums; font-family: "Segoe UI", Helvetica, sans-serif; }
table { width: 100%; border-collapse: collapse; font-family: "Segoe UI", Helvetica, sans-serif; font-size: 0.92rem; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
code, pre, ol.code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.82rem; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 8px; }
.pane { background: #f3eee4; border-radius: 6px; overflow: auto; }
.pane header {
  font-family: "Segoe UI", Helvetica, sans-serif; font-size: 0.82rem;
  padding: 6px 10px; color: var(--muted);
}
ol.code { margin: 0; padding: 8px 12px 12px 48px; }
ol.code li { white-space: pre; }
.notes { color: var(--muted); font-size: 0.95rem; }
.signal { margin: 0 0 16px; }
footer { width: min(1120px, calc(100% - 32px)); margin: 8px auto 32px; color: var(--muted); font-size: 0.9rem; }
@media (max-width: 800px) {
  .meta, .pair { grid-template-columns: 1fr; }
  h1 { font-size: 1.6rem; }
}
"""


def output_paths(prefix: Path) -> tuple[Path, Path, Path]:
    if prefix.exists() and prefix.is_dir():
        base = prefix / "lineage-report"
    else:
        base = prefix
    return base.with_suffix(".md"), base.with_suffix(".json"), base.with_suffix(".html")


def write_report(report: Report, prefix: Path) -> tuple[Path, Path, Path]:
    markdown_path, json_path, html_path = output_paths(prefix)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(render_json(report), encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    return markdown_path, json_path, html_path


def render_json(report: Report) -> str:
    payload = {
        "schema_version": 1,
        "tool": "lineage",
        "tool_version": __version__,
        "generated_at": report.generated_at,
        "disclaimer": DISCLAIMER,
        "how_to_read": HOW_TO_READ,
        "parameters": report.parameters,
        "original": report.original.to_dict(),
        "rewrite": report.rewrite.to_dict(),
        "narrative": report.narrative,
        "signals": [signal.to_dict() for signal in report.signals],
        "skipped": report.skipped,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_markdown(report: Report) -> str:
    lines: list[str] = [
        "# Lineage similarity report",
        "",
        f"> {DISCLAIMER}",
        "",
        HOW_TO_READ,
        "",
        f"Generated {report.generated_at} by lineage {__version__}.",
        "",
        "## Projects",
        "",
        _side_md("Original", report.original.to_dict()),
        "",
        _side_md("Rewrite", report.rewrite.to_dict()),
        "",
        "## Summary",
        "",
        report.narrative,
        "",
        "| Signal | Score | Band |",
        "| --- | ---: | --- |",
    ]
    for signal in report.signals:
        score = "n/a" if signal.score is None else f"{signal.score:.2f}"
        lines.append(f"| {signal.name} | {score} | {signal.band} |")
    for signal in report.signals:
        lines.extend(["", f"## {signal.name}", "", signal.summary, ""])
        for note in signal.notes:
            lines.append(f"_{note}_")
            lines.append("")
        metrics = {key: value for key, value in signal.metrics.items() if key != "file_matches"}
        if metrics:
            lines.append("| Metric | Value |")
            lines.append("| --- | --- |")
            for key, value in metrics.items():
                rendered = "n/a" if value is None else str(value)
                lines.append(f"| {key} | {rendered} |")
            lines.append("")
        matches = signal.metrics.get("file_matches")
        if isinstance(matches, list) and matches:
            lines.extend(
                [
                    "| Rewrite file | Original file | Containment | Shared fingerprints |",
                    "| --- | --- | ---: | ---: |",
                ]
            )
            for row in matches:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    "| {rewrite} | {original} | {containment:.2f} | {shared} |".format(
                        rewrite=_cell(str(row.get("rewrite_path", ""))),
                        original=_cell(str(row.get("original_path", ""))),
                        containment=float(row.get("containment", 0.0)),
                        shared=row.get("shared_fingerprints", 0),
                    )
                )
            lines.append("")
        if signal.evidence:
            lines.append("### Aligned regions")
            lines.append("")
            for index, item in enumerate(signal.evidence, start=1):
                lines.append(f"#### {index}. {item.detail}")
                lines.append("")
                lines.append(f"- Original `{_loc(item, 'original')}`")
                lines.append(f"- Rewrite `{_loc(item, 'rewrite')}`")
                lines.append("")
                if item.original_excerpt:
                    lines.append("Original:")
                    lines.append("")
                    lines.append(_fence(item.original_excerpt))
                    lines.append("")
                if item.rewrite_excerpt:
                    lines.append("Rewrite:")
                    lines.append("")
                    lines.append(_fence(item.rewrite_excerpt))
                    lines.append("")
        elif signal.score is not None:
            lines.append("No region cleared the display threshold.")
            lines.append("")
    if report.skipped:
        lines.extend(["", "## Files left out", ""])
        for skipped in report.skipped[:40]:
            lines.append(
                f"- {skipped.get('side', '')}: `{skipped.get('path', '')}` ({skipped.get('reason', '')})"
            )
        lines.append("")
    lines.extend(["", "---", "", DISCLAIMER, ""])
    return "\n".join(lines)


def render_html(report: Report) -> str:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Lineage similarity report</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        '<header class="top">',
        "<h1>Lineage similarity report</h1>",
        f'<p class="sub">lineage {html.escape(__version__)} · {html.escape(report.generated_at)}</p>',
        f'<aside class="disclaimer"><strong>READ THIS FIRST</strong><p>{html.escape(DISCLAIMER)}</p></aside>',
        f'<p class="howto">{html.escape(HOW_TO_READ)}</p>',
        '<nav class="toc">',
    ]
    for signal in report.signals:
        parts.append(f'<a href="#{html.escape(signal.id)}">{html.escape(signal.name)}</a>')
    parts.append("</nav></header><main>")
    parts.append('<section class="meta">')
    parts.append(_side_html("Original", report.original.to_dict()))
    parts.append(_side_html("Rewrite", report.rewrite.to_dict()))
    parts.append("</section>")
    parts.append(f"<p>{html.escape(report.narrative)}</p>")
    parts.append('<section class="cards">')
    for signal in report.signals:
        parts.append(_card(signal))
    parts.append("</section>")
    for signal in report.signals:
        parts.append(_signal_html(signal))
    if report.skipped:
        parts.append("<h2>Files left out</h2><ul>")
        for item in report.skipped[:40]:
            parts.append(
                "<li>"
                + html.escape(str(item.get("side", "")))
                + ": <code>"
                + html.escape(str(item.get("path", "")))
                + "</code> ("
                + html.escape(str(item.get("reason", "")))
                + ")</li>"
            )
        parts.append("</ul>")
    parts.append("</main>")
    parts.append(f"<footer><p>{html.escape(DISCLAIMER)}</p></footer>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _card(signal: SignalResult) -> str:
    if signal.score is None:
        width = 0
        label = "n/a"
    else:
        width = max(0, min(100, int(round(signal.score * 100))))
        label = f"{signal.score:.2f}"
    return (
        f'<a class="card" href="#{html.escape(signal.id)}">'
        f'<div class="band {html.escape(signal.band)}">{html.escape(signal.band)}</div>'
        f"<h3>{html.escape(signal.name)}</h3>"
        f'<div class="score">{label}</div>'
        f'<div class="bar"><span style="width:{width}%"></span></div>'
        "</a>"
    )


def _signal_html(signal: SignalResult) -> str:
    chunks = [
        f'<section class="signal" id="{html.escape(signal.id)}">',
        f"<h2>{html.escape(signal.name)}</h2>",
        f'<p class="band {html.escape(signal.band)}">{html.escape(signal.band)}</p>',
        f"<p>{html.escape(signal.summary)}</p>",
    ]
    for note in signal.notes:
        chunks.append(f'<p class="notes">{html.escape(note)}</p>')
    matches = signal.metrics.get("file_matches")
    if isinstance(matches, list) and matches:
        chunks.append(
            "<table><thead><tr><th>Rewrite file</th><th>Original file</th>"
            "<th>Containment</th><th>Shared</th></tr></thead><tbody>"
        )
        for row in matches:
            if not isinstance(row, dict):
                continue
            chunks.append(
                "<tr><td><code>{rewrite}</code></td><td><code>{original}</code></td><td>{containment:.2f}</td><td>{shared}</td></tr>".format(
                    rewrite=html.escape(str(row.get("rewrite_path", ""))),
                    original=html.escape(str(row.get("original_path", ""))),
                    containment=float(row.get("containment", 0.0)),
                    shared=html.escape(str(row.get("shared_fingerprints", ""))),
                )
            )
        chunks.append("</tbody></table>")
    if not signal.evidence:
        chunks.append("<p>No line-level evidence was recorded for this signal.</p>")
    for item in signal.evidence:
        chunks.append('<article class="region">')
        chunks.append(f"<p>{html.escape(item.detail)}</p>")
        chunks.append('<div class="pair">')
        chunks.append(_pane("Original", _loc(item, "original"), item.original_excerpt, item.original_start))
        chunks.append(_pane("Rewrite", _loc(item, "rewrite"), item.rewrite_excerpt, item.rewrite_start))
        chunks.append("</div></article>")
    chunks.append("</section>")
    return "\n".join(chunks)


def _pane(title: str, location: str, excerpt: str, start: int) -> str:
    return (
        '<div class="pane"><header>'
        + html.escape(title)
        + " <code>"
        + html.escape(location)
        + "</code></header>"
        + _code(excerpt, start)
        + "</div>"
    )


def _code(excerpt: str, start: int) -> str:
    if not excerpt:
        return "<p class='notes'>No excerpt.</p>"
    items: list[str] = []
    number = start if start > 0 else 1
    for line in excerpt.splitlines():
        if line == "…":
            items.append("<li class='ellipsis'>…</li>")
            continue
        shown = html.escape(line) if line else " "
        items.append(f'<li value="{number}">{shown}</li>')
        number += 1
    return '<ol class="code">' + "".join(items) + "</ol>"


def _side_html(title: str, info: dict[str, object]) -> str:
    lang = _language_summary(info)
    revision = info.get("revision") or "not a git checkout"
    return (
        '<div class="card"><h3>'
        + html.escape(title)
        + "</h3><p><code>"
        + html.escape(str(info.get("path", "")))
        + "</code></p><p>"
        + html.escape(f"Revision: {revision}")
        + "</p><p>"
        + html.escape(
            f"{info.get('files_compared', 0)} files, {info.get('loc', 0)} non-empty lines, "
            f"{info.get('files_skipped', 0)} left out. {lang}."
        )
        + "</p></div>"
    )


def _side_md(title: str, info: dict[str, object]) -> str:
    lang = _language_summary(info)
    revision = info.get("revision") or "not a git checkout"
    return (
        f"**{title}.** `{info.get('path', '')}` · revision `{revision}` · "
        f"{info.get('files_compared', 0)} files · {info.get('loc', 0)} non-empty lines · "
        f"{info.get('files_skipped', 0)} left out · {lang}."
    )


def _language_summary(info: dict[str, object]) -> str:
    raw = info.get("languages")
    if not isinstance(raw, dict) or not raw:
        return "none"
    return ", ".join(f"{key} {value}" for key, value in raw.items())


def _loc(item: Evidence, side: str) -> str:
    if side == "original":
        path, start, end = item.original_path, item.original_start, item.original_end
    else:
        path, start, end = item.rewrite_path, item.rewrite_start, item.rewrite_end
    if start <= 0:
        return path
    if end <= start:
        return f"{path}:{start}"
    return f"{path}:{start}-{end}"


def _fence(text: str) -> str:
    tick = "```"
    while tick in text:
        tick += "`"
    return f"{tick}\n{text}\n{tick}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|")
