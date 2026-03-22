"""
app.py
------
Flask web application for the AI-Powered Legacy Code Modernization Engine.
Now supports:
  - Async task-based processing with real-time progress polling
  - Sample file loader endpoints
  - Download endpoint
  - Logs viewer
"""

import os
import time
import uuid
import threading
import logging
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify,
    send_file, session
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

from chunker import chunk_code, detect_language
from modernizer import modernize_all_chunks
from utils import (
    setup_logging, generate_diff_html, compute_metrics,
    allowed_file, get_output_filename, read_log_tail
)

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-me')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['SAMPLES_FOLDER'] = 'samples'

for folder in ['uploads', 'outputs', 'samples']:
    Path(folder).mkdir(exist_ok=True)

setup_logging('logs.txt')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# In-memory task store (thread-safe)
# ─────────────────────────────────────────────
tasks: dict = {}
tasks_lock = threading.Lock()


def _new_task() -> dict:
    return {
        'status': 'pending',       # pending | running | done | error
        'stage': '',               # Human-readable current stage
        'chunks_done': 0,
        'chunks_total': 0,
        'result': None,
        'error': None,
    }


def _set_task(task_id: str, **kwargs):
    with tasks_lock:
        tasks[task_id].update(kwargs)


def _get_task(task_id: str) -> dict | None:
    with tasks_lock:
        return tasks.get(task_id)


# ─────────────────────────────────────────────
# Background worker
# ─────────────────────────────────────────────

def _run_modernization(task_id: str, original_code: str, filename: str,
                       model: str, upload_path: str):
    """Run in a background thread; updates task state as it goes."""
    try:
        _set_task(task_id, status='running', stage='Detecting language & chunking code…')

        # ── Chunk ──────────────────────────────────
        start = time.time()
        chunks, language = chunk_code(original_code, filename)
        total = len(chunks)
        logger.info(f"[{task_id}] Chunked into {total} chunk(s) | language: {language}")

        _set_task(task_id, stage=f'Language detected: {language.upper()} · {total} chunk(s) found',
                  chunks_total=total, chunks_done=0)

        # ── Progress callback ──────────────────────
        def on_chunk_done(done: int, total: int):
            _set_task(task_id,
                      stage=f'Modernizing chunk {done}/{total}…',
                      chunks_done=done)
            logger.info(f"[{task_id}] Chunk {done}/{total} complete")

        # ── Modernize ──────────────────────────────
        _set_task(task_id, stage='Sending chunks to AI model…')
        modernized_code, explanations = modernize_all_chunks(
            chunks, language, model,
            progress_callback=on_chunk_done
        )

        elapsed = time.time() - start

        # ── Save output ────────────────────────────
        _set_task(task_id, stage='Saving output file…')
        output_filename = get_output_filename(filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(modernized_code)
        logger.info(f"[{task_id}] Output saved: {output_filename}")

        # ── Diff ───────────────────────────────────
        _set_task(task_id, stage='Generating diff visualization…')
        try:
            diff_html = generate_diff_html(original_code, modernized_code)
        except Exception as e:
            logger.warning(f"Diff failed: {e}")
            diff_html = '<tr><td colspan="4" class="text-center p-4">Diff unavailable</td></tr>'

        # ── Metrics ────────────────────────────────
        _set_task(task_id, stage='Computing code metrics…')
        metrics = compute_metrics(original_code, modernized_code, language, elapsed)
        logger.info(f"[{task_id}] Metrics: {metrics}")

        # ── Store result ───────────────────────────
        with tasks_lock:
            tasks[task_id].update({
                'status': 'done',
                'stage': 'Complete',
                'chunks_done': total,
                'result': {
                    'success': True,
                    'original_code': original_code,
                    'modernized_code': modernized_code,
                    'diff_html': diff_html,
                    'metrics': metrics,
                    'explanations': explanations,
                    'chunks_count': total,
                    'language': language,
                    'output_filename': output_filename,
                    'output_path': output_path,
                }
            })

    except ValueError as e:
        logger.error(f"[{task_id}] Config error: {e}")
        _set_task(task_id, status='error', error=str(e))
    except Exception as e:
        logger.error(f"[{task_id}] Unexpected error: {e}")
        _set_task(task_id, status='error', error=f'Unexpected error: {str(e)}')


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/modernize', methods=['POST'])
def modernize():
    """
    Validate upload, start background task, return task_id immediately.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type. Allowed: .py, .java, .cbl, .cob, .js, .ts, .c, .cpp, .cs, .rb, .go'}), 400

    model = request.form.get('model', 'gemini-2.5-flash')
    filename = secure_filename(file.filename)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)
    logger.info(f"File uploaded: {filename}")

    try:
        with open(upload_path, 'r', encoding='utf-8', errors='replace') as f:
            original_code = f.read()
    except Exception as e:
        return jsonify({'error': f'Could not read file: {e}'}), 500

    if not original_code.strip():
        return jsonify({'error': 'Uploaded file is empty.'}), 400

    # Quick language pre-detection so UI shows it immediately
    language = detect_language(filename)

    # Create task
    task_id = str(uuid.uuid4())
    with tasks_lock:
        tasks[task_id] = _new_task()
        tasks[task_id]['language'] = language
        tasks[task_id]['filename'] = filename

    # Launch background thread
    t = threading.Thread(
        target=_run_modernization,
        args=(task_id, original_code, filename, model, upload_path),
        daemon=True
    )
    t.start()

    return jsonify({'task_id': task_id, 'language': language})


@app.route('/progress/<task_id>')
def progress(task_id: str):
    """Return current task progress as JSON (polled by frontend)."""
    task = _get_task(task_id)
    if task is None:
        # Task not yet registered or server was restarted — return a
        # soft 'pending' response so the client retries instead of crashing.
        return jsonify({
            'status': 'pending',
            'stage': 'Waiting for task to start…',
            'chunks_done': 0,
            'chunks_total': 0,
            'language': '',
            'filename': '',
            'error': None,
        }), 200

    payload = {
        'status': task['status'],
        'stage': task.get('stage', ''),
        'chunks_done': task.get('chunks_done', 0),
        'chunks_total': task.get('chunks_total', 0),
        'language': task.get('language', ''),
        'filename': task.get('filename', ''),
        'error': task.get('error'),
    }

    if task['status'] == 'done' and task['result']:
        result = task['result']
        # Store output path in session so /download works
        session['output_path'] = result['output_path']
        session['output_filename'] = result['output_filename']
        payload['result'] = {k: v for k, v in result.items() if k != 'output_path'}

    return jsonify(payload)


@app.route('/download')
def download():
    """Download the last modernized output file."""
    output_path = session.get('output_path')
    output_filename = session.get('output_filename', 'modernized_output.txt')
    if not output_path or not os.path.exists(output_path):
        return jsonify({'error': 'No output file available.'}), 404
    return send_file(output_path, as_attachment=True, download_name=output_filename)


@app.route('/sample/<lang>')
def sample(lang: str):
    """Serve a sample legacy code file for demo purposes."""
    lang_map = {
        'python': ('legacy_python.py', 'text/x-python'),
        'java':   ('legacy_java.java', 'text/x-java'),
        'cobol':  ('legacy_cobol.cbl', 'text/plain'),
    }
    if lang not in lang_map:
        return jsonify({'error': 'Unknown sample language.'}), 404

    filename, mime = lang_map[lang]
    path = os.path.join(app.config['SAMPLES_FOLDER'], filename)
    if not os.path.exists(path):
        return jsonify({'error': 'Sample file not found on server.'}), 404

    return send_file(path, mimetype=mime, as_attachment=False, download_name=filename)


@app.route('/logs')
def view_logs():
    log_content = read_log_tail('logs.txt', lines=100)
    return jsonify({'logs': log_content})


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 5 MB.'}), 413


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error. Check logs.'}), 500


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == '__main__':
    logger.info("Starting AI Legacy Code Modernization Engine (v2)…")
    # Render sets the $PORT environment variable automatically.
    # use_reloader=False is CRITICAL — the Werkzeug reloader forks a fresh
    # child process on every file-change, which wipes the in-memory `tasks`
    # dictionary and causes 'Task not found' errors mid-processing.
    port = int(os.environ.get('PORT', 5000))
    app.run(
        debug=False,
        host='0.0.0.0',
        port=port,
        threaded=True,
        use_reloader=False,
    )
