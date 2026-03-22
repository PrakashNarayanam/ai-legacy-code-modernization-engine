"""
modernizer.py
-------------
Google Gemini-powered code modernization module.
Sends each chunk to the Gemini API and aggregates results.
"""

import time
import logging
import os
import json
import re

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Safety settings — disable content blocks for code
# ─────────────────────────────────────────────
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH:       HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ─────────────────────────────────────────────
# Language-specific system prompts
# ─────────────────────────────────────────────

SYSTEM_PROMPTS = {
    'python': """You are an expert Python modernization engineer.
Refactor the provided legacy Python 2.x or old Python 3.x code into clean, modern Python 3.12+ code.

Apply ALL of the following modernizations:
- Replace print statements with print() functions
- Use f-strings instead of % formatting or .format()
- Add type hints to all function signatures
- Replace os.path with pathlib.Path where appropriate
- Use context managers (with statements) for file/resource handling
- Replace manual loops with list/dict comprehensions where readable
- Use logging instead of print() for debug output
- Apply PEP 8 style (snake_case, proper spacing, 4-space indentation)
- Replace deprecated APIs with modern equivalents
- Add proper docstrings if missing

RULES:
- Preserve ALL business logic exactly — do NOT change what the code does
- Return ONLY the raw refactored code
- Do NOT include markdown fences (no ```)
- Do NOT add any explanation text before or after the code""",

    'java': """You are an expert Java modernization engineer.
Refactor the provided legacy Java (Java 6/7/8) code into clean, modern Java 17+ code.

Apply ALL of the following modernizations:
- Use `var` for local variable type inference where appropriate
- Replace traditional for-loops with Streams API (.stream(), .map(), .filter(), .collect())
- Use try-with-resources for all AutoCloseable resources
- Replace null checks with Optional<T>
- Use List.of(), Map.of() for immutable collections
- Apply records for simple data classes (Java 16+)
- Use enhanced switch expressions (Java 14+)
- Add @Override annotations wherever applicable
- Replace StringBuffer with StringBuilder
- Apply modern Date/Time API (java.time.*) instead of java.util.Date

RULES:
- Preserve ALL business logic exactly
- Return ONLY the raw refactored code
- Do NOT include markdown fences (no ```)
- Do NOT add any explanation before or after the code""",

    'cobol': """You are an expert COBOL modernization engineer.
Refactor the provided legacy COBOL code into modern, readable COBOL following current best practices.

Apply ALL of the following modernizations:
- Replace GO TO statements with structured PERFORM loops
- Use EVALUATE instead of nested IF-ELSE chains
- Replace obsolete verbs with modern equivalents
- Use intrinsic functions (FUNCTION LENGTH, FUNCTION UPPER-CASE, etc.)
- Add clear inline comments and section headers
- Break oversized paragraphs into focused, well-named sections
- Use COMPUTE instead of verbose ADD/SUBTRACT/MULTIPLY/DIVIDE chains
- Ensure proper WORKING-STORAGE definitions with meaningful names
- Remove dead code and unused variables

RULES:
- Preserve ALL business logic exactly
- Return ONLY the raw refactored code
- Do NOT include markdown fences (no ```)
- Do NOT add any text before or after the COBOL code""",
}

DEFAULT_SYSTEM_PROMPT = """You are an expert software engineer specializing in code modernization.
Refactor the provided legacy code using current best practices for readability, performance,
and maintainability. Preserve all logic exactly.
Return ONLY the raw refactored code. Do NOT include markdown fences or any explanation."""

EXPLANATION_PROMPT = """Now briefly explain the improvements you just made to that code block.
Respond in this EXACT JSON format (no extra text, no markdown):
{
  "summary": "One-sentence summary of the main improvement",
  "improvements": [
    {"what": "Specific change made", "why": "Reason this improves the code"},
    {"what": "Specific change made", "why": "Reason this improves the code"},
    {"what": "Specific change made", "why": "Reason this improves the code"}
  ]
}
Limit to the 3 most impactful improvements."""


# ─────────────────────────────────────────────
# Gemini client setup
# ─────────────────────────────────────────────

def _configure_gemini():
    """Configure the Gemini SDK with the API key from environment."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key.strip() in ('', 'your_gemini_api_key_here'):
        raise ValueError(
            "GEMINI_API_KEY is not set. Please add your Google Gemini API key to the .env file."
        )
    genai.configure(api_key=api_key)
    logger.info("Gemini API configured successfully.")


def _get_model(model_name: str = 'gemini-2.5-flash') -> genai.GenerativeModel:
    """Return a configured Gemini GenerativeModel instance."""
    return genai.GenerativeModel(
        model_name=model_name,
        safety_settings=SAFETY_SETTINGS,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096,
        )
    )


# ─────────────────────────────────────────────
# Core modernization
# ─────────────────────────────────────────────

def modernize_chunk(
    chunk: dict,
    language: str,
    model: genai.GenerativeModel,
    retries: int = 3,
    retry_delay: float = 3.0,
) -> tuple[str, dict | None]:
    """
    Modernize a single code chunk using the Gemini API.

    Returns:
        (modernized_code: str, explanation: dict | None)
    """
    system_prompt = SYSTEM_PROMPTS.get(language, DEFAULT_SYSTEM_PROMPT)

    # Build the full prompt (Gemini uses a single-turn prompt style)
    full_prompt = (
        f"{system_prompt}\n\n"
        f"Modernize this {language.upper()} code block "
        f"(type: {chunk['type']}, name: {chunk['name']}):\n\n"
        f"{chunk['content']}"
    )

    modernized = None

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Gemini API call — chunk '{chunk['name']}' | attempt {attempt}/{retries}")

            response = model.generate_content(full_prompt)
            raw = response.text.strip()
            modernized = _strip_fences(raw)
            logger.info(f"Chunk '{chunk['name']}' modernized successfully ({len(modernized)} chars).")
            break

        except Exception as e:
            err_str = str(e)
            logger.warning(f"Attempt {attempt} failed for chunk '{chunk['name']}': {err_str}")
            if attempt < retries:
                wait = retry_delay * attempt
                logger.info(f"Retrying in {wait}s…")
                time.sleep(wait)

    if modernized is None:
        logger.error(f"All {retries} attempts failed for '{chunk['name']}'. Returning original.")
        return chunk['content'], None

    # Get explanation as a second call
    explanation = _get_explanation(model, language, chunk, modernized)
    return modernized, explanation


def _get_explanation(
    model: genai.GenerativeModel,
    language: str,
    original_chunk: dict,
    modernized_code: str,
) -> dict | None:
    """Ask Gemini to explain the improvements in structured JSON."""
    prompt = (
        f"I just refactored this {language.upper()} code block "
        f"(name: {original_chunk['name']}).\n\n"
        f"ORIGINAL:\n{original_chunk['content']}\n\n"
        f"MODERNIZED:\n{modernized_code}\n\n"
        f"{EXPLANATION_PROMPT}"
    )
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Extract JSON object from response
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        logger.warning(f"Could not generate explanation for '{original_chunk['name']}': {e}")
    return None


def _strip_fences(code: str) -> str:
    """Remove markdown code fences if Gemini included them."""
    lines = code.splitlines()
    # Remove opening fence (e.g. ```python or ```)
    if lines and lines[0].strip().startswith('```'):
        lines = lines[1:]
    # Remove closing fence
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    return '\n'.join(lines)


# ─────────────────────────────────────────────
# Full file modernization (called by app.py)
# ─────────────────────────────────────────────

def modernize_all_chunks(
    chunks: list[dict],
    language: str,
    model_name: str = 'gemini-2.5-flash',
    progress_callback=None,
) -> tuple[str, list[dict]]:
    """
    Modernize all chunks using Gemini and combine into final output.

    Args:
        chunks:            List of chunk dicts from chunker.py
        language:          Detected language string
        model_name:        Gemini model name to use
        progress_callback: Optional callable(done, total) for progress updates

    Returns:
        (combined_modernized_code: str, explanations: list[dict])
    """
    # Configure API key once
    _configure_gemini()
    model = _get_model(model_name)

    modernized_parts = []
    explanations = []
    total = len(chunks)

    logger.info(f"Starting Gemini modernization — {total} chunk(s) | model: {model_name} | language: {language}")

    for i, chunk in enumerate(chunks, start=1):
        logger.info(f"Processing chunk {i}/{total}: [{chunk['type']}] {chunk['name']}")

        modernized, explanation = modernize_chunk(chunk, language, model)
        modernized_parts.append(modernized)

        if explanation:
            explanation['chunk_name'] = chunk['name']
            explanation['chunk_type'] = chunk['type']
        else:
            explanation = {
                'chunk_name': chunk['name'],
                'chunk_type': chunk['type'],
                'summary': 'Explanation unavailable (API issue or empty response).',
                'improvements': [],
            }
        explanations.append(explanation)

        if progress_callback:
            progress_callback(i, total)

    combined = '\n\n'.join(modernized_parts)
    logger.info(f"Gemini modernization complete. Output size: {len(combined)} chars")
    return combined, explanations
