"""
Styles Package

CSS styling for report rendering. Separated from rendering logic
to allow easy customization and theming.
"""

from .base_styles import get_base_css
from .pdf_styles import get_pdf_css
from .academic_styles import get_academic_css


def get_html_styles(standalone: bool = False, report_type: str = 'summary') -> str:
    """Get CSS for HTML rendering."""
    css = get_base_css()
    if report_type == 'detailed':
        css += get_academic_css()
    return css


def get_pdf_styles(report_type: str = 'summary') -> str:
    """Get CSS for PDF rendering (includes print optimizations)."""
    css = get_base_css() + get_pdf_css()
    if report_type == 'detailed':
        css += get_academic_css()
    return css


__all__ = [
    'get_html_styles',
    'get_pdf_styles',
]
