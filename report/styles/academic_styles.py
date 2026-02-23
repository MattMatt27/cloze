"""
Academic CSS Styles

Publication-quality styling for detailed reports. Scoped under
.unified-report.academic-report to override base styles only when active.
"""


def get_academic_css() -> str:
    """Get academic CSS for detailed report rendering."""
    return """
    /* ===== Academic Report Overrides ===== */

    .unified-report.academic-report {
        font-family: Georgia, 'Times New Roman', Times, serif;
        max-width: 800px;
        box-shadow: none;
        border-radius: 0;
        border: 1px solid #ccc;
    }

    /* Header: no gradient, plain styling */
    .unified-report.academic-report .report-header {
        background: #ffffff;
        color: #000000;
        padding: 2.5rem 2rem 1.5rem 2rem;
        text-align: left;
        border-bottom: 2px solid #000;
    }

    .unified-report.academic-report .report-header h2 {
        font-size: 1.6rem;
        font-weight: 700;
        color: #000;
        font-family: Georgia, 'Times New Roman', Times, serif;
    }

    .unified-report.academic-report .window-description {
        color: #333;
        font-style: italic;
    }

    .unified-report.academic-report .report-type-badge {
        background: none;
        color: #555;
        border: none;
        padding: 0;
        font-style: italic;
        font-size: 0.95rem;
    }

    /* Meta: inline text, no colored boxes */
    .unified-report.academic-report .report-meta {
        display: block;
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #333;
    }

    .unified-report.academic-report .meta-item {
        background: none;
        padding: 0.25rem 0;
        text-align: left;
        border-radius: 0;
    }

    .unified-report.academic-report .meta-label {
        color: #555;
        font-size: 0.85rem;
    }

    .unified-report.academic-report .meta-value {
        color: #000;
        font-weight: 600;
    }

    /* Hide emoji icons */
    .unified-report.academic-report .component-icon {
        display: none;
    }

    /* Section headings: serif, plain rule */
    .unified-report.academic-report .component-header {
        border-bottom: 1px solid #999;
        border-top: none;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
    }

    .unified-report.academic-report .component-title {
        font-family: Georgia, 'Times New Roman', Times, serif;
        font-size: 1.2rem;
        font-weight: 700;
        color: #000;
    }

    .unified-report.academic-report .section-number {
        margin-right: 0.5rem;
    }

    /* Report sections */
    .unified-report.academic-report .report-section {
        padding: 1.5rem 2rem;
        border-bottom: none;
    }

    .unified-report.academic-report .report-content {
        padding: 0;
    }

    /* Stat cards: plain bordered cells instead of gradient cards */
    .unified-report.academic-report .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0;
        border: 1px solid #999;
        margin: 1rem 0;
    }

    .unified-report.academic-report .stat-card {
        background: #fff;
        color: #000;
        padding: 0.75rem;
        border-radius: 0;
        border-right: 1px solid #ccc;
        border-bottom: 1px solid #ccc;
        text-align: center;
    }

    .unified-report.academic-report .stat-card:nth-child(3n) {
        border-right: none;
    }

    .unified-report.academic-report .stat-card:nth-last-child(-n+3) {
        border-bottom: none;
    }

    .unified-report.academic-report .stat-value {
        color: #000;
        font-size: 1.4rem;
        font-weight: 700;
    }

    .unified-report.academic-report .stat-label {
        color: #555;
        font-size: 0.8rem;
    }

    /* Stat items (cooccurrence stats row) */
    .unified-report.academic-report .stat-item {
        background: #fff;
        color: #000;
        padding: 0.75rem;
        border-radius: 0;
        border: 1px solid #ccc;
    }

    .unified-report.academic-report .stat-item .stat-value {
        color: #000;
    }

    .unified-report.academic-report .stat-item .stat-label {
        color: #555;
    }

    /* NLP cards: single column, no colored borders */
    .unified-report.academic-report .nlp-grid {
        display: block;
    }

    .unified-report.academic-report .nlp-card {
        border: 1px solid #ccc;
        border-radius: 0;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .unified-report.academic-report .nlp-title {
        color: #000;
        font-family: Georgia, 'Times New Roman', Times, serif;
    }

    .unified-report.academic-report .sentiment-score {
        color: #000;
    }

    /* Progress bars: grayscale */
    .unified-report.academic-report .progress-bar {
        background: #e0e0e0;
        border-radius: 0;
        height: 10px;
    }

    .unified-report.academic-report .progress-fill {
        border-radius: 0;
    }

    .unified-report.academic-report .progress-positive { background: #444; }
    .unified-report.academic-report .progress-neutral  { background: #999; }
    .unified-report.academic-report .progress-negative  { background: #222; }
    .unified-report.academic-report .progress-active    { background: #444; }
    .unified-report.academic-report .progress-passive   { background: #999; }

    /* Tables: academic styling with top/bottom rules */
    .unified-report.academic-report .breakdown-table {
        border-top: 2px solid #000;
        border-bottom: 2px solid #000;
        font-family: Georgia, 'Times New Roman', Times, serif;
    }

    .unified-report.academic-report .breakdown-table th {
        background: #fff;
        border-bottom: 1px solid #000;
        font-weight: 700;
        color: #000;
    }

    .unified-report.academic-report .breakdown-table td {
        border-bottom: 1px solid #ddd;
        color: #000;
    }

    /* Interpretive prose */
    .unified-report.academic-report .interpretive-text {
        font-size: 1rem;
        line-height: 1.8;
        color: #000;
        margin: 0.75rem 0;
        text-indent: 0;
    }

    /* Figure container and captions */
    .unified-report.academic-report .figure-container {
        margin: 1.5rem 0;
        text-align: center;
    }

    .unified-report.academic-report .figure-caption {
        font-style: italic;
        font-size: 0.9rem;
        color: #333;
        margin-top: 0.75rem;
        text-align: left;
        line-height: 1.5;
    }

    /* Table captions: above table, italic */
    .unified-report.academic-report .table-caption {
        font-style: italic;
        font-size: 0.9rem;
        color: #333;
        margin-bottom: 0.5rem;
        margin-top: 1rem;
    }

    /* Co-occurrence graph: plain border */
    .unified-report.academic-report .cooccurrence-graph {
        border: 1px solid #ccc;
        border-radius: 0;
        padding: 1rem;
    }

    .unified-report.academic-report .graph-caption {
        font-style: italic;
        color: #333;
    }

    /* Top words: plain list */
    .unified-report.academic-report .top-words-section {
        background: #fff;
        border-radius: 0;
        border-left: none;
        padding: 1rem 0;
    }

    .unified-report.academic-report .top-words-section h4 {
        color: #000;
        font-family: Georgia, 'Times New Roman', Times, serif;
    }

    .unified-report.academic-report .word-item {
        border-radius: 0;
        border: none;
        border-bottom: 1px solid #eee;
        padding: 0.4rem 0;
    }

    .unified-report.academic-report .word-count {
        background: none;
        color: #000;
        padding: 0;
        font-weight: 400;
    }

    .unified-report.academic-report .word-text {
        color: #000;
    }

    /* Saved messages: academic blockquote style */
    .unified-report.academic-report .saved-message {
        background: #fff;
        border-left: 3px solid #999;
        border-radius: 0;
        padding: 0.75rem 1rem;
    }

    .unified-report.academic-report .message-text {
        color: #000;
        font-style: italic;
    }

    .unified-report.academic-report .message-note {
        color: #333;
    }

    .unified-report.academic-report .message-date {
        color: #666;
    }

    /* AI Summary / Executive Summary */
    .unified-report.academic-report .summary-content {
        border: none;
        padding: 0;
    }

    .unified-report.academic-report .summary-text {
        color: #000;
        line-height: 1.8;
    }

    .unified-report.academic-report .summary-text p {
        text-indent: 0;
    }

    .unified-report.academic-report .themes-section {
        border-top: none;
        padding-top: 1rem;
    }

    .unified-report.academic-report .themes-section h4 {
        color: #000;
        font-family: Georgia, 'Times New Roman', Times, serif;
    }

    .unified-report.academic-report .themes-list-simple li {
        color: #000;
    }

    .unified-report.academic-report .progress-notes {
        border-top: none;
        padding-top: 1rem;
    }

    .unified-report.academic-report .progress-notes h4 {
        color: #000;
        font-family: Georgia, 'Times New Roman', Times, serif;
    }

    .unified-report.academic-report .progress-notes-text {
        color: #000;
    }

    /* Methodology section */
    .unified-report.academic-report .methodology-section {
        background: #fff;
    }

    .unified-report.academic-report .methodology-intro {
        color: #000;
    }

    .unified-report.academic-report .methodology-list li {
        color: #000;
        border-bottom: none;
        padding: 0.4rem 0;
    }

    /* Citations / References section */
    .unified-report.academic-report .citations-section {
        background: #fff;
        border-top: 1px solid #000;
    }

    .unified-report.academic-report .citations-list {
        color: #000;
        font-size: 0.9rem;
    }

    .unified-report.academic-report .citations-list li {
        margin-bottom: 0.4rem;
    }

    /* Keyword counts */
    .unified-report.academic-report .keyword-row {
        border-bottom: 1px solid #eee;
    }

    .unified-report.academic-report .keyword-label {
        color: #000;
    }

    .unified-report.academic-report .keyword-value {
        color: #000;
    }

    /* Error message */
    .unified-report.academic-report .error-message {
        background: #fff;
        border-left: 3px solid #999;
    }

    .unified-report.academic-report .error-message p {
        color: #000;
    }

    /* Generated-by footer */
    .unified-report.academic-report .generated-by {
        font-size: 0.8rem;
        color: #666;
    }

    /* Subsection headings (h4 within components) */
    .unified-report.academic-report h4 {
        font-family: Georgia, 'Times New Roman', Times, serif;
        font-weight: 600;
        color: #000;
        font-size: 1.05rem;
        margin-top: 1.25rem;
        margin-bottom: 0.75rem;
    }

    /* No-data text */
    .unified-report.academic-report .no-data {
        color: #333;
        font-style: italic;
    }

    /* Print styles */
    @media print {
        .unified-report.academic-report {
            border: none;
            max-width: 100%;
        }
        .unified-report.academic-report .report-header {
            border-bottom: 1px solid #000;
        }
        .unified-report.academic-report .report-section {
            page-break-inside: avoid;
        }
    }
    """
