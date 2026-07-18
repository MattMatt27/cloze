"""Report-v2 document renderer. Pure — report_data dict in, HTML/CSV out.

The document is self-contained (inline CSS, inline SVG charts, no JS, no
external assets) so the same HTML serves the in-app viewer, the HTML
download, and weasyprint PDF conversion unchanged.

``links`` maps group keys (e.g. ``"window:12"``) to URLs of child-scope
reports — the drill-down affordance. The renderer never decides what links
exist; the route layer resolves them against actual Report rows.
"""

import html
import io
import csv as csv_module
from datetime import datetime, timezone

SCOPE_LABELS = {
    "conversation": "Conversation report",
    "window": "Phase report",
    "enrollment": "Participant study report",
    "participant": "Participant overview",
    "flow": "Cohort report",
    "account": "Study account report",
}

# Render order (registry order, narrative first)
_SECTION_ORDER = [
    "ai_summary", "hierarchical_summary", "descriptive_stats",
    "trend_analysis", "phase_comparison", "sentiment_analysis",
    "voice_analysis", "keyword_analysis", "cooccurrence",
    "completion_analysis", "engagement_overview",
]

_CSS = """
.cz-report { max-width: 720px; margin: 0 auto; padding: 32px 24px;
  font-family: Georgia, 'Times New Roman', serif; color: #1c1917; line-height: 1.6; }
.cz-report h1 { font-size: 26px; margin: 0 0 4px; }
.cz-report .cz-subtitle { color: #78716c; font-size: 14px; margin-bottom: 28px; }
.cz-report h2 { font-size: 18px; margin: 32px 0 10px; border-bottom: 1px solid #e7e5e4;
  padding-bottom: 6px; }
.cz-report h3 { font-size: 15px; margin: 18px 0 6px; }
.cz-report p { margin: 8px 0; }
.cz-statgrid { display: flex; flex-wrap: wrap; gap: 12px; margin: 12px 0; }
.cz-stat { flex: 1 1 120px; border: 1px solid #e7e5e4; border-radius: 8px;
  padding: 10px 12px; text-align: center; }
.cz-stat .cz-num { font-size: 20px; font-weight: 700; display: block; }
.cz-stat .cz-lbl { font-size: 11px; color: #78716c; text-transform: uppercase;
  letter-spacing: 0.04em; }
.cz-report table { border-collapse: collapse; width: 100%; margin: 12px 0;
  font-size: 13px; }
.cz-report th, .cz-report td { border: 1px solid #e7e5e4; padding: 6px 8px;
  text-align: left; }
.cz-report th { background: #fafaf9; font-weight: 600; }
.cz-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
.cz-chip { background: #f5f5f4; border-radius: 999px; padding: 2px 10px;
  font-size: 12px; }
.cz-group-summary { border-left: 3px solid #d6d3d1; padding-left: 12px;
  margin: 10px 0; }
.cz-note { color: #78716c; font-size: 12px; font-style: italic; }
.cz-report a.cz-drill { color: #4338ca; text-decoration: none; }
.cz-report a.cz-drill:hover { text-decoration: underline; }
.cz-chart { margin: 10px 0; }
@media print { .cz-report { max-width: none; padding: 0; } }
"""


def _esc(value):
    return html.escape(str(value)) if value is not None else ""


def _fmt_date(epoch):
    if epoch is None:
        return "—"
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%b %d, %Y")


def _fmt_num(value, digits=1):
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _stat(label, value):
    return (f'<div class="cz-stat"><span class="cz-num">{_esc(value)}</span>'
            f'<span class="cz-lbl">{_esc(label)}</span></div>')


def _line_chart(points, *, width=640, height=140, value_fmt=_fmt_num):
    """Inline SVG line chart for a [{label, value}] series (None-safe)."""
    usable = [(i, p) for i, p in enumerate(points) if p.get("value") is not None]
    if len(usable) < 2:
        return '<p class="cz-note">Not enough data points for a chart.</p>'
    values = [p["value"] for _, p in usable]
    vmin, vmax = min(values), max(values)
    span = (vmax - vmin) or 1.0
    pad, label_h = 8, 24
    plot_w, plot_h = width - 2 * pad, height - 2 * pad - label_h
    step = plot_w / (len(points) - 1) if len(points) > 1 else 0

    def xy(index, value):
        x = pad + index * step
        y = pad + plot_h * (1 - (value - vmin) / span)
        return x, y

    coords = [xy(i, p["value"]) for i, p in usable]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#4338ca">'
        f'<title>{_esc(points[i]["label"])}: {_esc(value_fmt(points[i]["value"]))}</title></circle>'
        for (x, y), (i, _) in zip(coords, usable)
    )
    labels = "".join(
        f'<text x="{pad + i * step:.1f}" y="{height - 6}" font-size="10" '
        f'fill="#78716c" text-anchor="middle">{_esc(str(p["label"])[:14])}</text>'
        for i, p in enumerate(points)
    )
    return (f'<svg class="cz-chart" viewBox="0 0 {width} {height}" '
            f'width="100%" role="img">'
            f'<polyline points="{polyline}" fill="none" stroke="#4338ca" '
            f'stroke-width="2"/>{dots}{labels}</svg>')


# --- section renderers --------------------------------------------------------

def _render_summary(section, links):
    parts = [f"<p>{_esc(section.get('summary'))}</p>"]
    for group in section.get("groups", []):
        link = links.get(group.get("key"))
        heading = _esc(group["label"])
        if link:
            heading = f'<a class="cz-drill" href="{_esc(link)}">{heading} →</a>'
        parts.append(f'<div class="cz-group-summary"><h3>{heading}</h3>'
                     f'<p>{_esc(group["summary"])}</p></div>')
    return "".join(parts)


def _render_descriptive(section, links):
    stats = "".join([
        _stat("Conversations", section["conversations"]),
        _stat("Messages", section["total_messages"]),
        _stat("Participant messages", section["user_messages"]),
        _stat("Active days", section["active_days"]),
        _stat("Avg msgs / conversation",
              _fmt_num(section["avg_messages_per_conversation"])),
        _stat("Avg words / participant msg",
              _fmt_num(section["avg_user_words_per_message"])),
    ])
    period = (f'<p class="cz-note">Activity from '
              f'{_fmt_date(section.get("first_message_at"))} to '
              f'{_fmt_date(section.get("last_message_at"))}.</p>')
    return f'<div class="cz-statgrid">{stats}</div>{period}'


def _render_trends(section, links):
    parts = []
    for key, title, fmt in [
        ("sentiment", "Sentiment over time", lambda v: _fmt_num(v, 2)),
        ("message_volume", "Message volume", _fmt_num),
        ("engagement", "Messages per conversation", _fmt_num),
        ("user_words_per_message", "Words per participant message", _fmt_num),
    ]:
        series = section.get(key) or []
        parts.append(f"<h3>{title}</h3>" + _line_chart(series, value_fmt=fmt))
    return "".join(parts)


def _render_comparison(section, links):
    rows = section.get("rows", [])
    body = "".join(
        "<tr><td>{label}</td><td>{convs}</td><td>{msgs}</td><td>{avg}</td>"
        "<td>{sent}</td><td>{days}</td></tr>".format(
            label=(f'<a class="cz-drill" href="{_esc(links[row["key"]])}">'
                   f'{_esc(row["label"])}</a>' if row["key"] in links
                   else _esc(row["label"])),
            convs=row["conversations"], msgs=row["user_messages"],
            avg=_fmt_num(row["avg_messages_per_conversation"]),
            sent=_fmt_num(row["sentiment_mean"], 2),
            days=row["active_days"],
        ) for row in rows)
    return ("<table><thead><tr><th>Period</th><th>Conversations</th>"
            "<th>Participant msgs</th><th>Avg msgs/conv</th><th>Sentiment</th>"
            "<th>Active days</th></tr></thead><tbody>" + body + "</tbody></table>")


def _render_sentiment(section, links):
    dist = section.get("percentages", {})
    stats = "".join([
        _stat("Mean", _fmt_num(section.get("mean"), 2)),
        _stat("Median", _fmt_num(section.get("median"), 2)),
        _stat("Positive", f'{_fmt_num(dist.get("positive"))}%'),
        _stat("Neutral", f'{_fmt_num(dist.get("neutral"))}%'),
        _stat("Negative", f'{_fmt_num(dist.get("negative"))}%'),
    ])
    return (f'<div class="cz-statgrid">{stats}</div>'
            f'<p class="cz-note">Across {section.get("analyzed_messages", 0)} '
            f'participant messages (TextBlob polarity).</p>')


def _render_voice(section, links):
    return ('<div class="cz-statgrid">'
            + _stat("Active voice", f'{_fmt_num(section["active_ratio"])}%')
            + _stat("Passive voice", f'{_fmt_num(section["passive_ratio"])}%')
            + "</div>")


def _render_keywords(section, links):
    chips = "".join(
        f'<span class="cz-chip">{_esc(category)}: {count}</span>'
        for category, count in sorted(section.get("emotional_keywords", {}).items())
    )
    return (f'<div class="cz-chips">{chips}</div>'
            f'<p>{section.get("question_count", 0)} questions asked '
            f'({_fmt_num(section.get("questions_per_user_message", 0) * 100)}% '
            f'of participant messages).</p>')


def _render_cooccurrence(section, links):
    words = "".join(
        f'<span class="cz-chip">{_esc(w["word"])} ({w["count"]})</span>'
        for w in section.get("top_words", [])[:15])
    rows = "".join(
        f'<tr><td>{_esc(p["pair"][0])} + {_esc(p["pair"][1])}</td>'
        f'<td>{p["count"]}</td></tr>'
        for p in section.get("pairs", [])[:15])
    return (f'<h3>Frequent words</h3><div class="cz-chips">{words}</div>'
            f'<h3>Word pairs</h3><table><thead><tr><th>Pair</th><th>Count</th>'
            f'</tr></thead><tbody>{rows}</tbody></table>')


def _render_completion(section, links):
    stats = "".join([
        _stat("Enrolled", section.get("enrolled", 0)),
        _stat("Started", section.get("started", 0)),
        _stat("Started %", f'{_fmt_num(section.get("started_pct"))}%'),
    ])
    out = f'<div class="cz-statgrid">{stats}</div>'
    participation = section.get("phase_participation")
    if participation:
        rows = "".join(f"<tr><td>{_esc(phase)}</td><td>{count}</td></tr>"
                       for phase, count in participation.items())
        out += ("<h3>Participation by phase</h3><table><thead><tr>"
                "<th>Phase</th><th>Active participants</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
    by_flow = section.get("by_flow")
    if by_flow:
        rows = "".join(
            f'<tr><td>{_esc(f["name"])}</td><td>{f["enrollment_count"]}</td>'
            f'<td>{f["started_count"]}</td></tr>' for f in by_flow)
        out += ("<h3>By flow</h3><table><thead><tr><th>Flow</th><th>Enrolled"
                "</th><th>Started</th></tr></thead><tbody>" + rows
                + "</tbody></table>")
    inactive = section.get("inactive")
    if inactive:
        out += ('<p class="cz-note">Enrolled but inactive: '
                + _esc(", ".join(inactive)) + "</p>")
    return out


def _render_engagement(section, links):
    rows = "".join(
        "<tr><td>{label}</td><td>{convs}</td><td>{msgs}</td><td>{days}</td>"
        "<td>{sent}</td><td>{last}</td></tr>".format(
            label=(f'<a class="cz-drill" href="{_esc(links[row["key"]])}">'
                   f'{_esc(row["label"])}</a>' if row["key"] in links
                   else _esc(row["label"])),
            convs=row["conversations"], msgs=row["total_messages"],
            days=row["active_days"], sent=_fmt_num(row["sentiment_mean"], 2),
            last=_fmt_date(row["last_message_at"]),
        ) for row in section.get("rows", []))
    return ("<table><thead><tr><th>Flow</th><th>Conversations</th>"
            "<th>Messages</th><th>Active days</th><th>Sentiment</th>"
            "<th>Last activity</th></tr></thead><tbody>" + rows
            + "</tbody></table>")


_RENDERERS = {
    "ai_summary": ("Summary", _render_summary),
    "hierarchical_summary": ("Summary", _render_summary),
    "descriptive_stats": ("Overview", _render_descriptive),
    "trend_analysis": ("Trends over time", _render_trends),
    "phase_comparison": ("Period comparison", _render_comparison),
    "sentiment_analysis": ("Sentiment", _render_sentiment),
    "voice_analysis": ("Voice", _render_voice),
    "keyword_analysis": ("Emotional keywords", _render_keywords),
    "cooccurrence": ("Word co-occurrence", _render_cooccurrence),
    "completion_analysis": ("Completion", _render_completion),
    "engagement_overview": ("Engagement by flow", _render_engagement),
}


def render_document(report_data, links=None):
    """The report as a self-contained HTML fragment (style + article)."""
    links = links or {}
    sections = report_data.get("sections", {})
    body = []
    for key in _SECTION_ORDER:
        section = sections.get(key)
        if section is None:
            continue
        heading, renderer = _RENDERERS[key]
        body.append(f'<section><h2>{_esc(heading)}</h2>'
                    f'{renderer(section, links)}</section>')

    scope_label = SCOPE_LABELS.get(report_data.get("scope"), "Report")
    generated = _fmt_date(report_data.get("generated_at"))
    return (
        f"<style>{_CSS}</style>"
        f'<article class="cz-report">'
        f'<h1>{_esc(report_data.get("title"))}</h1>'
        f'<p class="cz-subtitle">{_esc(scope_label)} · '
        f'{report_data.get("conversation_count", 0)} conversation(s) · '
        f'generated {generated}</p>'
        + "".join(body) +
        '<p class="cz-note">Generated by CLOZE report system v2. Analyses are '
        'automated aids, not clinical judgments.</p>'
        "</article>"
    )


def render_standalone_html(report_data, links=None):
    """Full HTML document (downloads and weasyprint PDF input)."""
    title = _esc(report_data.get("title", "Report"))
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{title}</title></head><body>"
            + render_document(report_data, links) + "</body></html>")


def render_csv(report_data, table="conversations"):
    """Tidy CSV for external analysis (R/SPSS).

    conversations: one row per conversation.
    groups: one row per group (phase/flow/participant) with headline stats.
    """
    buffer = io.StringIO()
    writer = csv_module.writer(buffer)
    if table == "conversations":
        writer.writerow(["conversation_id", "user_messages", "user_words",
                         "mean_sentiment", "duration_seconds"])
        for row in report_data.get("per_conversation", []):
            writer.writerow([
                row["conversation_id"], row["user_messages"], row["user_words"],
                "" if row["mean_sentiment"] is None else row["mean_sentiment"],
                row["duration_seconds"],
            ])
    elif table == "groups":
        writer.writerow(["group_key", "group_label", "conversations"])
        for group in report_data.get("groups", []):
            writer.writerow([group["key"], group["label"], group["conversations"]])
    else:
        raise ValueError(f"unknown csv table {table!r}")
    return buffer.getvalue()
