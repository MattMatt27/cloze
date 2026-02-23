"""
Base CSS Styles

Core styling for HTML reports. All CSS is scoped within .unified-report
to prevent conflicts with other page styles.

Design tokens (matching Cloze UI):
  page:         #FAF9F7
  surface:      #FFFFFF
  muted:        #F5F4F0
  cloze-indigo: #5B5FC7
  cloze-sky:    #7DBBDA
  cloze-hover:  #4E51B0
  stone-100:    #f5f5f4
  stone-200:    #e7e5e4
  stone-300:    #d6d3d1
  stone-400:    #a8a29e
  stone-500:    #78716c
  stone-700:    #44403c
  stone-800:    #292524
  stone-900:    #1c1917
"""


def get_base_css() -> str:
    """Get base CSS for HTML rendering."""
    return """
    .unified-report {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 1000px;
        margin: 0 auto;
        background: #ffffff;
        border-radius: 8px;
        border: 1px solid #e7e5e4;
        overflow: hidden;
    }

    .unified-report .report-header {
        background: #FAF9F7;
        color: #1c1917;
        padding: 2rem;
        text-align: center;
        border-bottom: 1px solid #e7e5e4;
    }

    .unified-report .report-header h2 {
        margin: 0 0 1rem 0;
        font-size: 1.75rem;
        font-weight: 600;
        color: #1c1917;
    }

    .unified-report .window-description {
        color: #78716c;
        margin-bottom: 1.5rem;
    }

    .unified-report .report-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 0.75rem;
        margin-top: 1.5rem;
    }

    .unified-report .meta-item {
        background: #ffffff;
        padding: 0.75rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e7e5e4;
    }

    .unified-report .meta-item-full {
        grid-column: 1 / -1;
    }

    .unified-report .meta-label {
        font-size: 0.8rem;
        color: #a8a29e;
        margin-bottom: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }

    .unified-report .meta-value {
        font-size: 1.1rem;
        font-weight: 600;
        color: #5B5FC7;
    }

    .unified-report .meta-value-models {
        font-size: 0.95rem;
        word-wrap: break-word;
    }

    .unified-report .report-content {
        padding: 0;
    }

    .unified-report .report-section {
        border-bottom: 1px solid #f5f5f4;
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
        border-bottom: 2px solid #F5F4F0;
    }

    .unified-report .component-icon {
        display: none;
    }

    .unified-report .component-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #a8a29e;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .unified-report .summary-text {
        font-size: 1rem;
        line-height: 1.7;
        color: #44403c;
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
        border-top: 1px solid #e7e5e4;
    }

    .unified-report .themes-section h4 {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1c1917;
        margin: 0 0 0.75rem 0;
    }

    .unified-report .themes-list-simple {
        list-style: disc;
        padding-left: 1.5rem;
        margin: 0;
    }

    .unified-report .themes-list-simple li {
        color: #44403c;
        margin: 0.5rem 0;
        line-height: 1.6;
    }

    .unified-report .themes-list {
        list-style: none;
        padding: 0;
        margin: 1rem 0;
    }

    .unified-report .themes-list li {
        background: #F5F4F0;
        margin: 0.5rem 0;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border-left: 3px solid #5B5FC7;
        color: #1c1917;
    }

    .unified-report .progress-notes {
        margin: 1.5rem 0 0 0;
        padding-top: 1.5rem;
        border-top: 1px solid #e7e5e4;
    }

    .unified-report .progress-notes h4 {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1c1917;
        margin: 0 0 0.75rem 0;
    }

    .unified-report .progress-notes-text {
        font-size: 1rem;
        line-height: 1.7;
        color: #44403c;
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
        gap: 0.75rem;
        margin: 1.5rem 0;
    }

    .unified-report .stat-card {
        background: #F5F4F0;
        color: #1c1917;
        padding: 1.25rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e7e5e4;
    }

    .unified-report .stat-value {
        display: block;
        font-size: 1.75rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        color: #5B5FC7;
    }

    .unified-report .stat-label {
        font-size: 0.8rem;
        color: #a8a29e;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }

    .unified-report .nlp-subsection {
        padding-bottom: 1.25rem;
        margin-bottom: 1.25rem;
        border-bottom: 1px solid #f5f5f4;
    }

    .unified-report .nlp-subsection:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
    }

    .unified-report .nlp-title {
        font-weight: 600;
        color: #292524;
        margin-bottom: 0.75rem;
        font-size: 0.95rem;
    }

    .unified-report .progress-bar {
        background: #F5F4F0;
        border-radius: 10px;
        height: 10px;
        margin: 0.5rem 0;
        overflow: hidden;
    }

    .unified-report .progress-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }

    .unified-report .progress-positive { background: #10b981; }
    .unified-report .progress-neutral { background: #a8a29e; }
    .unified-report .progress-negative { background: #ef4444; }
    .unified-report .progress-active { background: #5B5FC7; }
    .unified-report .progress-passive { background: #7DBBDA; }

    .unified-report .saved-message {
        background: #FAF9F7;
        border-left: 3px solid #5B5FC7;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }

    .unified-report .message-text {
        font-style: italic;
        color: #292524;
        margin-bottom: 0.5rem;
        font-size: 1.05rem;
    }

    .unified-report .message-note {
        color: #5B5FC7;
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
    }

    .unified-report .message-date {
        color: #a8a29e;
        font-size: 0.85rem;
        margin: 0;
    }

    .unified-report .generated-by {
        text-align: right;
        font-size: 0.85rem;
        color: #78716c;
        margin-top: 1rem;
        font-style: italic;
    }

    .unified-report .no-data {
        color: #78716c;
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
        color: #44403c;
    }

    .unified-report .nlp-note {
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #78716c;
    }

    .unified-report .sentiment-score {
        font-size: 1.2rem;
        font-weight: 600;
        color: #5B5FC7;
        margin-bottom: 1rem;
    }

    /* Co-occurrence Analysis Styles */
    .unified-report .cooccurrence-content {
        margin-top: 1rem;
    }

    .unified-report .cooccurrence-graph {
        background: #ffffff;
        border: 1px solid #e7e5e4;
        border-radius: 8px;
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
        color: #78716c;
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
        gap: 0.75rem;
    }

    .unified-report .stat-item {
        background: #F5F4F0;
        color: #1c1917;
        padding: 1.25rem;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e7e5e4;
    }

    .unified-report .stat-item .stat-value {
        color: #5B5FC7;
    }

    .unified-report .top-words-section {
        background: #FAF9F7;
        border-radius: 8px;
        padding: 1.5rem;
        border-left: 3px solid #5B5FC7;
    }

    .unified-report .top-words-section h4 {
        margin: 0 0 1rem 0;
        color: #292524;
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
        border: 1px solid #e7e5e4;
    }

    .unified-report .word-text {
        font-weight: 600;
        color: #292524;
        font-size: 1rem;
    }

    .unified-report .word-count {
        background: #5B5FC7;
        color: #ffffff;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .unified-report .error-message {
        background: #fffbeb;
        border-left: 3px solid #f59e0b;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }

    .unified-report .error-message p {
        color: #92400e;
        margin: 0;
    }

    /* Report Type Badge */
    .unified-report .report-type-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .unified-report .report-type-summary {
        background: #ede9fe;
        color: #7c3aed;
    }
    .unified-report .report-type-detailed {
        background: #ede9fe;
        color: #7c3aed;
        border: 1px solid #c4b5fd;
    }

    /* Methodology Section (Detailed mode) */
    .unified-report .methodology-section {
        background: #FAF9F7;
        padding: 2rem;
        border-bottom: 1px solid #e7e5e4;
    }
    .unified-report .methodology-intro {
        font-size: 0.95rem;
        color: #78716c;
        margin-bottom: 1rem;
    }
    .unified-report .methodology-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .unified-report .methodology-list li {
        padding: 0.6rem 0;
        border-bottom: 1px solid #e7e5e4;
        font-size: 0.95rem;
        color: #44403c;
    }
    .unified-report .methodology-list li:last-child {
        border-bottom: none;
    }

    /* Citations Section (Detailed mode) */
    .unified-report .citations-section {
        background: #FAF9F7;
        padding: 2rem;
        border-top: 1px solid #e7e5e4;
    }
    .unified-report .citations-list {
        padding-left: 1.5rem;
        font-size: 0.9rem;
        color: #78716c;
        margin: 0;
    }
    .unified-report .citations-list li {
        margin-bottom: 0.5rem;
    }

    /* Detailed-mode extras */
    .unified-report .detailed-breakdown {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e7e5e4;
    }
    .unified-report .detailed-breakdown h4 {
        font-size: 1rem;
        font-weight: 600;
        color: #292524;
        margin: 0 0 1rem 0;
    }
    .unified-report .breakdown-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    .unified-report .breakdown-table th {
        background: #F5F4F0;
        padding: 0.5rem 0.75rem;
        text-align: left;
        font-weight: 600;
        color: #292524;
        border-bottom: 2px solid #e7e5e4;
    }
    .unified-report .breakdown-table td {
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid #f5f5f4;
        color: #44403c;
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
        border-bottom: 1px solid #f5f5f4;
    }
    .unified-report .keyword-row:last-child {
        border-bottom: none;
    }
    .unified-report .keyword-label {
        font-size: 0.95rem;
        color: #44403c;
    }
    .unified-report .keyword-value {
        font-weight: 600;
        color: #5B5FC7;
        font-size: 1rem;
    }
    """
