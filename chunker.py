"""
chunker.py
----------
Intelligent code chunking module for the Legacy Code Modernization Engine.
Detects functions/classes and splits code without breaking logical units.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Maximum tokens per chunk (approximate: 1 token ≈ 4 characters)
MAX_CHUNK_CHARS = 3000
MIN_CHUNK_CHARS = 200


def detect_language(filename: str) -> str:
    """Detect programming language from file extension."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    language_map = {
        'py': 'python',
        'java': 'java',
        'cbl': 'cobol',
        'cob': 'cobol',
        'cpy': 'cobol',
        'js': 'javascript',
        'ts': 'typescript',
        'c': 'c',
        'cpp': 'cpp',
        'cs': 'csharp',
        'rb': 'ruby',
        'go': 'go',
    }
    return language_map.get(ext, 'unknown')


def _split_python(code: str) -> list[dict]:
    """
    Split Python code into chunks by top-level functions and classes.
    Returns a list of dicts with 'type', 'name', and 'content'.
    """
    chunks = []
    # Match class or function definitions at the top level (no leading whitespace)
    pattern = re.compile(r'^(class\s+\w+|def\s+\w+)', re.MULTILINE)
    matches = list(pattern.finditer(code))

    if not matches:
        # No structure found — return whole code as one chunk
        return [{'type': 'block', 'name': 'module', 'content': code.strip()}]

    # Capture any header (imports, comments) before the first function/class
    header = code[:matches[0].start()].strip()
    if header:
        chunks.append({'type': 'header', 'name': 'imports/header', 'content': header})

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(code)
        block = code[start:end].strip()
        block_type = 'class' if match.group().startswith('class') else 'function'
        name = match.group().split()[-1].rstrip(':')
        chunks.append({'type': block_type, 'name': name, 'content': block})

    return chunks


def _split_java(code: str) -> list[dict]:
    """
    Split Java code into chunks by class and method definitions.
    """
    chunks = []
    # Match class declarations
    class_pattern = re.compile(
        r'((?:public|private|protected|abstract|final|\s)*\s*class\s+\w+[^{]*\{)',
        re.MULTILINE
    )
    # Match method declarations inside class
    method_pattern = re.compile(
        r'((?:public|private|protected|static|final|synchronized|\s)*\s+'
        r'(?:\w+(?:<[^>]+>)?)\s+\w+\s*\([^)]*\)\s*(?:throws\s+\w+\s*)?\{)',
        re.MULTILINE
    )

    matches = list(class_pattern.finditer(code))
    if not matches:
        # Try splitting by methods alone
        method_matches = list(method_pattern.finditer(code))
        if not method_matches:
            return [{'type': 'block', 'name': 'java_code', 'content': code.strip()}]
        for i, match in enumerate(method_matches):
            start = match.start()
            end = method_matches[i + 1].start() if i + 1 < len(method_matches) else len(code)
            chunks.append({'type': 'method', 'name': match.group().split('(')[0].split()[-1], 'content': code[start:end].strip()})
        return chunks

    # Return header (imports/package declaration)
    header = code[:matches[0].start()].strip()
    if header:
        chunks.append({'type': 'header', 'name': 'package/imports', 'content': header})

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(code)
        class_block = code[start:end].strip()
        class_name_match = re.search(r'class\s+(\w+)', match.group())
        class_name = class_name_match.group(1) if class_name_match else f'class_{i}'

        # Now split the class body into methods
        method_matches = list(method_pattern.finditer(class_block))
        if not method_matches or len(class_block) <= MAX_CHUNK_CHARS:
            chunks.append({'type': 'class', 'name': class_name, 'content': class_block})
        else:
            # Split large class into method-level chunks
            class_header = class_block[:method_matches[0].start()].strip()
            if class_header:
                chunks.append({'type': 'class_header', 'name': f'{class_name}_header', 'content': class_header})
            for j, m_match in enumerate(method_matches):
                m_start = m_match.start()
                m_end = method_matches[j + 1].start() if j + 1 < len(method_matches) else len(class_block)
                method_name = m_match.group().split('(')[0].split()[-1]
                chunks.append({
                    'type': 'method',
                    'name': f'{class_name}.{method_name}',
                    'content': class_block[m_start:m_end].strip()
                })
    return chunks


def _split_cobol(code: str) -> list[dict]:
    """
    Split COBOL code into DIVISION/SECTION chunks.
    """
    chunks = []
    # COBOL divisions
    division_pattern = re.compile(
        r'^[ \t]*([A-Z][A-Z\- ]+)\s+DIVISION\.',
        re.MULTILINE | re.IGNORECASE
    )
    section_pattern = re.compile(
        r'^[ \t]*([A-Z][A-Z0-9\- ]+)\s+SECTION\.',
        re.MULTILINE | re.IGNORECASE
    )

    matches = list(division_pattern.finditer(code))
    if not matches:
        # Fall back to section-level splitting
        matches = list(section_pattern.finditer(code))
    if not matches:
        return [{'type': 'block', 'name': 'cobol_code', 'content': code.strip()}]

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(code)
        block = code[start:end].strip()
        div_name = match.group().strip().rstrip('.')
        chunks.append({'type': 'division', 'name': div_name, 'content': block})

    return chunks


def _split_generic(code: str) -> list[dict]:
    """
    Generic line-based chunking for unsupported languages.
    Avoids splitting in the middle of a block (heuristic: blank lines as boundaries).
    """
    chunks = []
    lines = code.splitlines(keepends=True)
    current = []
    current_size = 0

    for line in lines:
        current.append(line)
        current_size += len(line)
        # Use blank lines as natural boundaries
        if current_size >= MAX_CHUNK_CHARS and line.strip() == '':
            chunks.append({
                'type': 'block',
                'name': f'block_{len(chunks) + 1}',
                'content': ''.join(current).strip()
            })
            current = []
            current_size = 0

    if current:
        chunks.append({
            'type': 'block',
            'name': f'block_{len(chunks) + 1}',
            'content': ''.join(current).strip()
        })

    return chunks if chunks else [{'type': 'block', 'name': 'block_1', 'content': code.strip()}]


def _merge_small_chunks(chunks: list[dict]) -> list[dict]:
    """
    Merge consecutive very small chunks to avoid too many API calls.
    """
    if not chunks:
        return chunks

    merged = [chunks[0]]
    for chunk in chunks[1:]:
        last = merged[-1]
        combined_size = len(last['content']) + len(chunk['content'])
        if combined_size < MIN_CHUNK_CHARS:
            merged[-1] = {
                'type': 'merged',
                'name': f"{last['name']} + {chunk['name']}",
                'content': last['content'] + '\n\n' + chunk['content']
            }
        else:
            merged.append(chunk)
    return merged


def _split_large_chunks(chunks: list[dict]) -> list[dict]:
    """
    Split any chunk exceeding MAX_CHUNK_CHARS into sub-chunks by line groups.
    """
    result = []
    for chunk in chunks:
        if len(chunk['content']) <= MAX_CHUNK_CHARS:
            result.append(chunk)
        else:
            lines = chunk['content'].splitlines(keepends=True)
            sub = []
            sub_size = 0
            sub_idx = 1
            for line in lines:
                sub.append(line)
                sub_size += len(line)
                if sub_size >= MAX_CHUNK_CHARS:
                    result.append({
                        'type': chunk['type'],
                        'name': f"{chunk['name']}_part{sub_idx}",
                        'content': ''.join(sub).strip()
                    })
                    sub = []
                    sub_size = 0
                    sub_idx += 1
            if sub:
                result.append({
                    'type': chunk['type'],
                    'name': f"{chunk['name']}_part{sub_idx}",
                    'content': ''.join(sub).strip()
                })
    return result


def chunk_code(code: str, filename: str) -> tuple[list[dict], str]:
    """
    Main entry point. Returns (list_of_chunks, detected_language).
    Each chunk: {'type': str, 'name': str, 'content': str}
    """
    language = detect_language(filename)
    logger.info(f"Chunking code | Language: {language} | File: {filename} | Size: {len(code)} chars")

    if language == 'python':
        chunks = _split_python(code)
    elif language == 'java':
        chunks = _split_java(code)
    elif language == 'cobol':
        chunks = _split_cobol(code)
    else:
        chunks = _split_generic(code)

    # Post-processing
    chunks = _merge_small_chunks(chunks)
    chunks = _split_large_chunks(chunks)

    logger.info(f"Created {len(chunks)} chunk(s) for '{filename}'")
    for i, c in enumerate(chunks):
        logger.debug(f"  Chunk {i+1}: [{c['type']}] {c['name']} ({len(c['content'])} chars)")

    return chunks, language
