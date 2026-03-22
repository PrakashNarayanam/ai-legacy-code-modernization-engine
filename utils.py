"""
utils.py
--------
Utility functions: diff generation, code metrics, logging setup.
"""

import difflib
import re
import time
import logging
import os
from datetime import datetime


# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────

def setup_logging(log_file: str = 'logs.txt') -> logging.Logger:
    """
    Configure root logger to write to both a file and the console.
    Returns the root logger.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s %(name)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


# ─────────────────────────────────────────────
# Diff Generation
# ─────────────────────────────────────────────

def generate_diff_html(original: str, modernized: str) -> str:
    """
    Generate an HTML side-by-side diff using difflib.
    Added lines are green, removed lines are red.
    Returns an HTML string of diff rows.
    """
    original_lines = original.splitlines(keepends=True)
    modernized_lines = modernized.splitlines(keepends=True)

    differ = difflib.Differ()
    diff = list(differ.compare(original_lines, modernized_lines))

    html_rows = []
    orig_line_num = 0
    mod_line_num = 0

    for line in diff:
        tag = line[:2]
        content = _escape_html(line[2:].rstrip('\n'))

        if tag == '  ':  # unchanged
            orig_line_num += 1
            mod_line_num += 1
            html_rows.append(
                f'<tr class="diff-unchanged">'
                f'<td class="diff-lnum">{orig_line_num}</td>'
                f'<td class="diff-code">{content}</td>'
                f'<td class="diff-lnum">{mod_line_num}</td>'
                f'<td class="diff-code">{content}</td>'
                f'</tr>'
            )
        elif tag == '- ':  # removed
            orig_line_num += 1
            html_rows.append(
                f'<tr class="diff-removed">'
                f'<td class="diff-lnum">{orig_line_num}</td>'
                f'<td class="diff-code diff-del">{content}</td>'
                f'<td class="diff-lnum"></td>'
                f'<td class="diff-code diff-del-empty"></td>'
                f'</tr>'
            )
        elif tag == '+ ':  # added
            mod_line_num += 1
            html_rows.append(
                f'<tr class="diff-added">'
                f'<td class="diff-lnum"></td>'
                f'<td class="diff-code diff-add-empty"></td>'
                f'<td class="diff-lnum">{mod_line_num}</td>'
                f'<td class="diff-code diff-add">{content}</td>'
                f'</tr>'
            )
        # Skip '? ' lines (diff hints)

    return '\n'.join(html_rows)


def generate_unified_diff(original: str, modernized: str, filename: str = 'code') -> str:
    """
    Generate a unified diff string for display in a <pre> block.
    """
    original_lines = original.splitlines(keepends=True)
    modernized_lines = modernized.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        modernized_lines,
        fromfile=f'original/{filename}',
        tofile=f'modernized/{filename}',
        lineterm=''
    )
    return '\n'.join(diff)


def _escape_html(text: str) -> str:
    """Escape HTML special characters in code lines."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


# ─────────────────────────────────────────────
# Code Metrics
# ─────────────────────────────────────────────

def compute_metrics(original: str, modernized: str, language: str, elapsed: float) -> dict:
    """
    Compute a metrics dictionary comparing original vs modernized code.
    """
    orig_lines = [l for l in original.splitlines() if l.strip()]
    mod_lines = [l for l in modernized.splitlines() if l.strip()]

    orig_loc = len(orig_lines)
    mod_loc = len(mod_lines)

    orig_funcs = count_functions(original, language)
    mod_funcs = count_functions(modernized, language)

    # Improvement heuristic: reduction in LOC + added modern patterns
    loc_reduction = max(0, orig_loc - mod_loc)
    modern_patterns = _count_modern_patterns(modernized, language)

    # Score: 0–100
    if orig_loc > 0:
        loc_score = min(30, (loc_reduction / orig_loc) * 100)
    else:
        loc_score = 0

    pattern_score = min(70, modern_patterns * 10)
    improvement_pct = round(loc_score + pattern_score, 1)

    return {
        'orig_loc': orig_loc,
        'mod_loc': mod_loc,
        'loc_change': mod_loc - orig_loc,
        'orig_funcs': orig_funcs,
        'mod_funcs': mod_funcs,
        'improvement_pct': improvement_pct,
        'processing_time': round(elapsed, 2),
        'language': language,
        'orig_chars': len(original),
        'mod_chars': len(modernized),
    }


def count_functions(code: str, language: str) -> int:
    """Count functions/methods in source code."""
    patterns = {
        'python': r'^\s*def\s+\w+',
        'java': r'(?:public|private|protected|static|final|synchronized|\s)+[\w<>\[\]]+\s+\w+\s*\(',
        'cobol': r'^\s*\w+[\w\-]*\s+SECTION\.',
        'javascript': r'(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\()',
        'typescript': r'(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s*)?\()',
        'go': r'^func\s+\w+',
        'c': r'^\w[\w\*\s]+\w+\s*\([^;]*\)\s*\{',
        'cpp': r'^\w[\w\*\s]+\w+\s*\([^;]*\)\s*\{',
    }
    pattern = patterns.get(language, r'^\s*def\s+\w+')
    try:
        matches = re.findall(pattern, code, re.MULTILINE)
        return len(matches)
    except re.error:
        return 0


def _count_modern_patterns(code: str, language: str) -> int:
    """
    Heuristically count modern language patterns in updated code.
    Each match adds to the improvement score.
    """
    patterns_map = {
        'python': [
            r'\bf-string\b|f[\'"]',         # f-strings
            r'\bwith\b.*\bas\b',             # context managers
            r'->',                           # type hints
            r'@\w+',                         # decorators
            r'\blist comprehension\b|\[.*for.*in.*\]',
            r'\blogging\b',                  # logging vs print
            r'\bpathlib\b|\bPath\(',         # pathlib
        ],
        'java': [
            r'\bvar\b',                      # local type inference (Java 10+)
            r'Optional\.',                   # Optional API
            r'\.stream\(\)',                 # Streams API
            r'@Override',                    # annotations
            r'List\.of\(|Map\.of\(',         # immutable collections
            r'try\s*\(',                     # try-with-resources
            r'\brecord\b',                   # records (Java 16+)
        ],
        'cobol': [
            r'FUNCTION\s+\w+',              # intrinsic functions
            r'EVALUATE',                     # EVALUATE vs GO TO
            r'PERFORM\s+\w+',               # structured PERFORM
        ],
    }

    ps = patterns_map.get(language, [])
    count = 0
    for p in ps:
        try:
            if re.search(p, code, re.MULTILINE | re.IGNORECASE):
                count += 1
        except re.error:
            pass
    return count


# ─────────────────────────────────────────────
# File Helpers
# ─────────────────────────────────────────────

ALLOWED_EXTENSIONS = {
    'py', 'java', 'cbl', 'cob', 'cpy',
    'js', 'ts', 'c', 'cpp', 'cs', 'rb', 'go'
}


def allowed_file(filename: str) -> bool:
    """Check if uploaded file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_output_filename(original_filename: str) -> str:
    """Return the output filename for the modernized code."""
    basename, ext = original_filename.rsplit('.', 1) if '.' in original_filename else (original_filename, 'txt')
    return f'modernized_output.{ext}'


def read_log_tail(log_file: str = 'logs.txt', lines: int = 50) -> str:
    """Read the last N lines of the log file."""
    if not os.path.exists(log_file):
        return 'No log file found.'
    with open(log_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    return ''.join(all_lines[-lines:])


def timestamp() -> str:
    """Return a human-readable timestamp string."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
