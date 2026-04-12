"""
Base CSS Styles

Core styling for HTML reports. All CSS is scoped within .unified-report
to prevent conflicts with other page styles.

Design: Document-style, matches the Cloze platform's text-forward approach.
No cards, no boxes. Data presented through typography, color, and spacing.
"""


def get_base_css() -> str:
    """Get base CSS for HTML rendering."""
    return """
    .unified-report {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 100%;
        margin: 0;
        background: transparent;
        color: #44403c;
        line-height: 1.7;
    }

    /* ── Header ─────────────────────────────────────────── */

    .unified-report .report-header {
        padding: 0 0 1.5rem 0;
        margin-bottom: 2rem;
    }

    .unified-report .report-header h2 {
        margin: 0 0 0.25rem 0;
        font-size: 1.5rem;
        font-weight: 700;
        color: #1c1917;
        line-height: 1.3;
    }

    .unified-report .report-type-badge {
        display: none;
    }

    .unified-report .window-description {
        color: #78716c;
        margin: 0.25rem 0 1.25rem 0;
        font-size: 0.95rem;
    }

    .unified-report .report-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid #f5f5f4;
    }

    .unified-report .meta-item {
        text-align: left;
    }

    .unified-report .meta-item-full {
        flex-basis: 100%;
    }

    .unified-report .meta-label {
        font-size: 0.7rem;
        color: #a8a29e;
        margin-bottom: 0.1rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 500;
    }

    .unified-report .meta-value {
        font-size: 1rem;
        font-weight: 600;
        color: #1c1917;
    }

    .unified-report .meta-value-models {
        font-size: 0.9rem;
        font-weight: 500;
        color: #78716c;
    }

    /* ── Content flow ───────────────────────────────────── */

    .unified-report .report-content {
        padding: 0;
    }

    .unified-report .report-section {
        padding: 0;
        margin-bottom: 2.5rem;
    }

    .unified-report .report-section:last-child {
        margin-bottom: 0;
    }

    .unified-report .component-header {
        margin-bottom: 1rem;
        padding: 0;
        border: none;
    }

    .unified-report .component-icon {
        display: none;
    }

    .unified-report .component-title {
        font-size: 0.7rem;
        font-weight: 600;
        color: #a8a29e;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ── AI Summary ─────────────────────────────────────── */

    .unified-report .summary-text {
        font-size: 0.95rem;
        line-height: 1.8;
        color: #44403c;
    }

    .unified-report .summary-text p {
        margin: 0 0 0.75rem 0;
    }

    .unified-report .summary-text p:last-child {
        margin-bottom: 0;
    }

    .unified-report .themes-section {
        margin: 1.5rem 0 0 0;
        padding-top: 1rem;
    }

    .unified-report .themes-section h4 {
        font-size: 0.85rem;
        font-weight: 600;
        color: #1c1917;
        margin: 0 0 0.5rem 0;
    }

    .unified-report .themes-list-simple {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .unified-report .themes-list-simple li {
        color: #44403c;
        margin: 0;
        padding: 0.4rem 0;
        border-bottom: 1px solid #fafaf9;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .unified-report .themes-list-simple li:last-child {
        border-bottom: none;
    }

    .unified-report .themes-list-simple li::before {
        content: "—";
        color: #d6d3d1;
        margin-right: 0.5rem;
    }

    .unified-report .themes-list {
        list-style: none;
        padding: 0;
        margin: 0.5rem 0;
    }

    .unified-report .themes-list li {
        padding: 0.5rem 0;
        padding-left: 0.75rem;
        border-left: 2px solid #c4b5fd;
        margin: 0.5rem 0;
        color: #44403c;
        font-size: 0.9rem;
    }

    .unified-report .progress-notes {
        margin: 1.5rem 0 0 0;
        padding-top: 1rem;
    }

    .unified-report .progress-notes h4 {
        font-size: 0.85rem;
        font-weight: 600;
        color: #1c1917;
        margin: 0 0 0.5rem 0;
    }

    .unified-report .progress-notes-text {
        font-size: 0.95rem;
        line-height: 1.8;
        color: #44403c;
    }

    .unified-report .progress-notes-text p {
        margin: 0 0 0.75rem 0;
    }

    .unified-report .progress-notes-text p:last-child {
        margin-bottom: 0;
    }

    .unified-report .progress-notes-text ul,
    .unified-report .progress-notes-text ol {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .unified-report .generated-by {
        font-size: 0.75rem;
        color: #d6d3d1;
        margin-top: 1rem;
    }

    /* ── Statistics ──────────────────────────────────────── */

    .unified-report .stats-grid,
    .unified-report .stats-row {
        display: flex;
        gap: 2rem;
        margin: 0;
    }

    .unified-report .stat-card,
    .unified-report .stat-item {
        background: transparent;
        padding: 0;
        text-align: left;
        border: none;
        border-radius: 0;
    }

    .unified-report .stat-value {
        display: block;
        font-size: 1.75rem;
        font-weight: 700;
        color: #1c1917;
        line-height: 1.2;
    }

    .unified-report .stat-label {
        font-size: 0.7rem;
        color: #a8a29e;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 500;
        margin-top: 0.15rem;
    }

    /* ── NLP Analysis ───────────────────────────────────── */

    .unified-report .nlp-subsection {
        padding-bottom: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .unified-report .nlp-subsection:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
    }

    .unified-report .nlp-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #1c1917;
        margin-bottom: 0.5rem;
    }

    .unified-report .sentiment-score {
        font-size: 1rem;
        font-weight: 600;
        color: #1c1917;
        margin-bottom: 0.75rem;
    }

    .unified-report .progress-bar {
        background: #f5f5f4;
        border-radius: 2px;
        height: 4px;
        margin: 0.35rem 0;
        overflow: hidden;
    }

    .unified-report .progress-fill {
        height: 100%;
        border-radius: 2px;
    }

    .unified-report .progress-positive { background: #10b981; }
    .unified-report .progress-neutral { background: #d6d3d1; }
    .unified-report .progress-negative { background: #f87171; }
    .unified-report .progress-active { background: #5B5FC7; }
    .unified-report .progress-passive { background: #7DBBDA; }

    .unified-report .progress-item {
        margin-bottom: 0.5rem;
    }

    .unified-report .progress-item span {
        display: block;
        margin-bottom: 0.15rem;
        font-size: 0.8rem;
        color: #78716c;
    }

    /* ── Saved Messages ─────────────────────────────────── */

    .unified-report .saved-message {
        border-left: 2px solid #c4b5fd;
        padding: 0.5rem 0 0.5rem 0.75rem;
        margin: 0.75rem 0;
    }

    .unified-report .saved-message .message-text {
        font-style: italic;
        color: #44403c;
        font-size: 0.9rem;
        line-height: 1.6;
        margin: 0;
    }

    .unified-report .saved-message .message-note {
        color: #78716c;
        font-size: 0.8rem;
        margin: 0.25rem 0 0 0;
    }

    .unified-report .saved-message .message-date {
        color: #d6d3d1;
        font-size: 0.75rem;
        margin: 0.25rem 0 0 0;
    }

    /* ── Co-occurrence ──────────────────────────────────── */

    .unified-report .cooccurrence-graph {
        background: transparent;
        border: none;
        padding: 0;
        margin-bottom: 1.5rem;
        text-align: center;
    }

    .unified-report .network-graph-image {
        max-width: 100%;
        height: auto;
        margin-bottom: 0.5rem;
    }

    .unified-report .graph-caption {
        font-size: 0.8rem;
        color: #a8a29e;
        font-style: italic;
        margin: 0;
    }

    .unified-report .top-words-section {
        padding: 0;
        background: transparent;
        border-left: 2px solid #c4b5fd;
        padding-left: 0.75rem;
    }

    .unified-report .top-words-section h4 {
        margin: 0 0 0.75rem 0;
        color: #1c1917;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .unified-report .top-words-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .unified-report .word-item {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: transparent;
        padding: 0;
        border: none;
    }

    .unified-report .word-text {
        font-weight: 500;
        color: #44403c;
        font-size: 0.85rem;
    }

    .unified-report .word-count {
        background: transparent;
        color: #a8a29e;
        padding: 0;
        font-size: 0.75rem;
        font-weight: 500;
    }

    .unified-report .word-count::before { content: "("; }
    .unified-report .word-count::after { content: ")"; }

    /* ── Keywords ────────────────────────────────────────── */

    .unified-report .keyword-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.35rem 0;
    }

    .unified-report .keyword-label {
        font-size: 0.85rem;
        color: #44403c;
    }

    .unified-report .keyword-value {
        font-weight: 600;
        color: #1c1917;
        font-size: 0.85rem;
    }

    /* ── Misc ────────────────────────────────────────────── */

    .unified-report .no-data {
        color: #d6d3d1;
        font-style: italic;
        padding: 1rem 0;
    }

    .unified-report .nlp-note {
        font-size: 0.8rem;
        color: #a8a29e;
        margin-top: 0.5rem;
    }

    .unified-report .error-message {
        border-left: 2px solid #f59e0b;
        padding: 0.5rem 0 0.5rem 0.75rem;
        margin: 0.75rem 0;
    }

    .unified-report .error-message p {
        color: #92400e;
        margin: 0;
        font-size: 0.9rem;
    }

    /* ── Detailed mode ──────────────────────────────────── */

    .unified-report .methodology-section {
        background: transparent;
        padding: 0 0 1.5rem 0;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid #f5f5f4;
    }

    .unified-report .methodology-intro {
        font-size: 0.9rem;
        color: #78716c;
        margin-bottom: 0.75rem;
    }

    .unified-report .methodology-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .unified-report .methodology-list li {
        padding: 0.4rem 0;
        font-size: 0.85rem;
        color: #44403c;
    }

    .unified-report .citations-section {
        background: transparent;
        padding: 1.5rem 0 0 0;
        border-top: 1px solid #f5f5f4;
        margin-top: 1.5rem;
    }

    .unified-report .citations-list {
        padding-left: 1.25rem;
        font-size: 0.8rem;
        color: #a8a29e;
        margin: 0;
    }

    .unified-report .citations-list li {
        margin-bottom: 0.35rem;
    }

    .unified-report .detailed-breakdown {
        margin-top: 1.5rem;
    }

    .unified-report .detailed-breakdown h4 {
        font-size: 0.85rem;
        font-weight: 600;
        color: #1c1917;
        margin: 0 0 0.75rem 0;
    }

    .unified-report .breakdown-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }

    .unified-report .breakdown-table th {
        background: transparent;
        padding: 0.4rem 0.5rem;
        text-align: left;
        font-weight: 600;
        color: #1c1917;
        border-bottom: 1px solid #e7e5e4;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .unified-report .breakdown-table td {
        padding: 0.4rem 0.5rem;
        border-bottom: 1px solid #fafaf9;
        color: #44403c;
    }
    """
