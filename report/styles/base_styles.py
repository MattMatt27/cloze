"""
Base CSS Styles

Core styling for HTML reports. All CSS is scoped within .unified-report
to prevent conflicts with other page styles.
"""


def get_base_css() -> str:
    """Get base CSS for HTML rendering."""
    return """
    .unified-report {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 1000px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        overflow: hidden;
    }

    .unified-report .report-header {
        background: linear-gradient(135deg, #0066cc 0%, #4a90e2 100%);
        color: #ffffff;
        padding: 2rem;
        text-align: center;
    }

    .unified-report .report-header h2 {
        margin: 0 0 1rem 0;
        font-size: 2rem;
        font-weight: 300;
        color: #ffffff;
    }

    .unified-report .window-description {
        color: rgba(255,255,255,0.9);
        margin-bottom: 1.5rem;
    }

    .unified-report .report-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin-top: 1.5rem;
    }

    .unified-report .meta-item {
        background: rgba(255,255,255,0.1);
        padding: 0.75rem;
        border-radius: 8px;
        text-align: center;
    }

    .unified-report .meta-item-full {
        grid-column: 1 / -1;
    }

    .unified-report .meta-label {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.9);
        margin-bottom: 0.25rem;
    }

    .unified-report .meta-value {
        font-size: 1.1rem;
        font-weight: 600;
        color: #ffffff;
    }

    .unified-report .meta-value-models {
        font-size: 0.95rem;
        word-wrap: break-word;
    }

    .unified-report .report-content {
        padding: 0;
    }

    .unified-report .report-section {
        border-bottom: 1px solid #f0f0f0;
        padding: 2rem;
    }

    .unified-report .report-section:last-child {
        border-bottom: none;
    }

    .unified-report .component-header {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid #e6f3ff;
    }

    .unified-report .component-icon {
        font-size: 1.5rem;
        margin-right: 0.75rem;
    }

    .unified-report .component-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #003d7a;
        margin: 0;
    }

    .unified-report .summary-content {
        background: #ffffff;
        border-radius: 8px;
        padding: 1.5rem;
        border: 1px solid #e0e0e0;
    }

    .unified-report .summary-text {
        font-size: 1rem;
        line-height: 1.7;
        color: #333;
        margin-bottom: 1.5rem;
    }

    .unified-report .summary-text p {
        margin: 0 0 1rem 0;
    }

    .unified-report .summary-text p:last-child {
        margin-bottom: 0;
    }

    .unified-report .themes-section {
        margin: 1.5rem 0;
        padding-top: 1.5rem;
        border-top: 1px solid #e0e0e0;
    }

    .unified-report .themes-section h4 {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0 0 0.75rem 0;
    }

    .unified-report .themes-list-simple {
        list-style: disc;
        padding-left: 1.5rem;
        margin: 0;
    }

    .unified-report .themes-list-simple li {
        color: #333;
        margin: 0.5rem 0;
        line-height: 1.6;
    }

    .unified-report .themes-list {
        list-style: none;
        padding: 0;
        margin: 1rem 0;
    }

    .unified-report .themes-list li {
        background: #e6f3ff;
        margin: 0.5rem 0;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border-left: 3px solid #0066cc;
        color: #1a1a1a;
    }

    .unified-report .progress-notes {
        margin: 1.5rem 0 0 0;
        padding-top: 1.5rem;
        border-top: 1px solid #e0e0e0;
    }

    .unified-report .progress-notes h4 {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 0 0 0.75rem 0;
    }

    .unified-report .progress-notes-text {
        font-size: 1rem;
        line-height: 1.7;
        color: #333;
    }

    .unified-report .progress-notes-text p {
        margin: 0 0 1rem 0;
        text-indent: 0;
    }

    .unified-report .progress-notes-text p:last-child {
        margin-bottom: 0;
    }

    /* Ensure no list styling bleeds into progress notes */
    .unified-report .progress-notes-text ul,
    .unified-report .progress-notes-text ol {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .unified-report .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0;
    }

    .unified-report .stat-card {
        background: linear-gradient(135deg, #0066cc 0%, #4a90e2 100%);
        color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
    }

    .unified-report .stat-value {
        display: block;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #ffffff;
    }

    .unified-report .stat-label {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.95);
    }

    .unified-report .nlp-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin-top: 1rem;
    }

    .unified-report .nlp-card {
        background: #ffffff;
        border: 2px solid #e6f3ff;
        border-radius: 12px;
        padding: 1.5rem;
    }

    .unified-report .nlp-title {
        font-weight: 600;
        color: #003d7a;
        margin-bottom: 1rem;
        font-size: 1.1rem;
    }

    .unified-report .progress-bar {
        background: #e6f3ff;
        border-radius: 10px;
        height: 12px;
        margin: 0.5rem 0;
        overflow: hidden;
    }

    .unified-report .progress-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }

    .unified-report .progress-positive { background: linear-gradient(90deg, #00a86b, #4fd1c7); }
    .unified-report .progress-neutral { background: linear-gradient(90deg, #808080, #b0b0b0); }
    .unified-report .progress-negative { background: linear-gradient(90deg, #ff6b6b, #ffa8a8); }
    .unified-report .progress-active { background: linear-gradient(90deg, #0066cc, #66b3ff); }
    .unified-report .progress-passive { background: linear-gradient(90deg, #9370db, #b19cd9); }

    .unified-report .saved-message {
        background: #f0f8ff;
        border-left: 4px solid #0066cc;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }

    .unified-report .message-text {
        font-style: italic;
        color: #003d7a;
        margin-bottom: 0.5rem;
        font-size: 1.05rem;
    }

    .unified-report .message-note {
        color: #0066cc;
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
    }

    .unified-report .message-date {
        color: #999;
        font-size: 0.85rem;
        margin: 0;
    }

    .unified-report .generated-by {
        text-align: right;
        font-size: 0.85rem;
        color: #666;
        margin-top: 1rem;
        font-style: italic;
    }

    .unified-report .no-data {
        color: #666;
        font-style: italic;
        text-align: center;
        padding: 2rem;
    }

    .unified-report .progress-item {
        margin-bottom: 1rem;
    }

    .unified-report .progress-item span {
        display: block;
        margin-bottom: 0.25rem;
        font-size: 0.9rem;
        color: #333;
    }

    .unified-report .nlp-note {
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #666;
    }

    .unified-report .sentiment-score {
        font-size: 1.2rem;
        font-weight: 600;
        color: #003d7a;
        margin-bottom: 1rem;
    }

    /* Co-occurrence Analysis Styles */
    .unified-report .cooccurrence-content {
        margin-top: 1rem;
    }

    .unified-report .cooccurrence-graph {
        background: #ffffff;
        border: 2px solid #e6f3ff;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        text-align: center;
    }

    .unified-report .network-graph-image {
        max-width: 100%;
        height: auto;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    .unified-report .graph-caption {
        font-size: 0.9rem;
        color: #666;
        font-style: italic;
        margin: 0;
        line-height: 1.4;
    }

    .unified-report .cooccurrence-stats {
        margin-bottom: 1.5rem;
    }

    .unified-report .stats-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
    }

    .unified-report .stat-item {
        background: linear-gradient(135deg, #0066cc 0%, #4a90e2 100%);
        color: #ffffff;
        padding: 1.25rem;
        border-radius: 10px;
        text-align: center;
    }

    .unified-report .top-words-section {
        background: #f0f8ff;
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 4px solid #0066cc;
    }

    .unified-report .top-words-section h4 {
        margin: 0 0 1rem 0;
        color: #003d7a;
        font-size: 1.1rem;
    }

    .unified-report .top-words-list {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0.75rem;
    }

    .unified-report .word-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #ffffff;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }

    .unified-report .word-text {
        font-weight: 600;
        color: #003d7a;
        font-size: 1rem;
    }

    .unified-report .word-count {
        background: #0066cc;
        color: #ffffff;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .unified-report .error-message {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }

    .unified-report .error-message p {
        color: #856404;
        margin: 0;
    }

    /* Report Type Badge */
    .unified-report .report-type-badge {
        display: inline-block;
        padding: 0.25rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .unified-report .report-type-summary {
        background: rgba(255,255,255,0.2);
        color: #ffffff;
    }
    .unified-report .report-type-detailed {
        background: rgba(255,255,255,0.3);
        color: #ffffff;
        border: 1px solid rgba(255,255,255,0.4);
    }

    /* Methodology Section (Detailed mode) */
    .unified-report .methodology-section {
        background: #f8fafc;
        padding: 2rem;
        border-bottom: 1px solid #f0f0f0;
    }
    .unified-report .methodology-intro {
        font-size: 0.95rem;
        color: #475569;
        margin-bottom: 1rem;
    }
    .unified-report .methodology-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .unified-report .methodology-list li {
        padding: 0.6rem 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 0.95rem;
        color: #334155;
    }
    .unified-report .methodology-list li:last-child {
        border-bottom: none;
    }

    /* Citations Section (Detailed mode) */
    .unified-report .citations-section {
        background: #f8fafc;
        padding: 2rem;
        border-top: 2px solid #e2e8f0;
    }
    .unified-report .citations-list {
        padding-left: 1.5rem;
        font-size: 0.9rem;
        color: #475569;
        margin: 0;
    }
    .unified-report .citations-list li {
        margin-bottom: 0.5rem;
    }

    /* Detailed-mode extras */
    .unified-report .detailed-breakdown {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e2e8f0;
    }
    .unified-report .detailed-breakdown h4 {
        font-size: 1rem;
        font-weight: 600;
        color: #334155;
        margin: 0 0 1rem 0;
    }
    .unified-report .breakdown-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    .unified-report .breakdown-table th {
        background: #f1f5f9;
        padding: 0.5rem 0.75rem;
        text-align: left;
        font-weight: 600;
        color: #334155;
        border-bottom: 2px solid #e2e8f0;
    }
    .unified-report .breakdown-table td {
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid #f1f5f9;
        color: #475569;
    }

    /* Emotional Keywords Card */
    .unified-report .keyword-counts {
        margin-top: 0.5rem;
    }
    .unified-report .keyword-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .unified-report .keyword-row:last-child {
        border-bottom: none;
    }
    .unified-report .keyword-label {
        font-size: 0.95rem;
        color: #334155;
    }
    .unified-report .keyword-value {
        font-weight: 600;
        color: #003d7a;
        font-size: 1rem;
    }
    """
