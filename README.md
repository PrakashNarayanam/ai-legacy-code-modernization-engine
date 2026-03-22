# CodeAscend — AI-Powered Legacy Code Modernization Engine

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![Gemini](https://img.shields.io/badge/Google%20Gemini-API-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952b3?style=for-the-badge&logo=bootstrap&logoColor=white)

**Upload legacy code → AI modernizes it → Download the result**

</div>

---

## Problem Statement

Millions of lines of legacy code (COBOL, Java 6/7, Python 2) power critical systems worldwide.
Maintaining and evolving these codebases is slow, expensive, and risky because:

- Legacy syntax is hard to read and maintain
- Old APIs and patterns reduce performance and safety
- Manual refactoring is error-prone and time-consuming
- Developers unfamiliar with old paradigms struggle to contribute

---

## Solution

**CodeAscend** uses Google Gemini AI to automatically modernize legacy source files by:

1. **Detecting the language** — Python, Java, COBOL, JavaScript, and more
2. **Chunking intelligently** — splits by functions/classes, not arbitrary lines
3. **Modernizing each chunk** — language-specific Gemini prompts per chunk
4. **Combining the output** — reassembled into a single downloadable file
5. **Explaining every change** — AI explains what was improved and why

---

## Features

| Feature | Description |
|---|---|
| 🤖 Google Gemini AI | Powered by Gemini 2.5 Flash / 2.0 Flash / 2.5 Pro |
| 🧩 Smart Chunking | Splits by `def`/`class` (Python), methods (Java), DIVISION (COBOL) |
| 📊 Real-Time Progress | Live progress bar with step-by-step status updates |
| 🌐 Language Detection | Auto-detects uploaded file language and shows badge |
| 🎨 Diff Viewer | Side-by-side diff with green (added) / red (removed) lines |
| 📈 Metrics Dashboard | LOC comparison, lines reduced, functions, improvement %, time |
| 💬 AI Explanations | Per-chunk explanations categorized as Performance / Readability / Optimization |
| 📂 Sample Files | Built-in legacy Python, Java, and COBOL demo files |
| 📥 Download | Download the modernized output file directly |
| 📋 Logs Viewer | Live processing logs visible from navbar |

---

## Project Structure

```
project/
│
├── app.py              ← Flask app, routes, async task manager
├── chunker.py          ← Language-aware code splitter
├── modernizer.py       ← Google Gemini API integration
├── utils.py            ← Diff, metrics, logging, file helpers
│
├── templates/
│   └── index.html      ← Single-page UI
│
├── static/
│   └── style.css       ← Dark glassmorphism theme
│
├── samples/
│   ├── legacy_python.py    ← Demo: Python 2 style code
│   ├── legacy_java.java    ← Demo: Java 7 style code
│   └── legacy_cobol.cbl    ← Demo: COBOL payroll program
│
├── uploads/            ← Temp uploaded files (auto-created)
├── outputs/            ← Modernized output files (auto-created)
├── logs.txt            ← Auto-generated processing log
│
├── requirements.txt
├── .env                ← API key (do NOT commit to Git)
└── README.md
```

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Add your Gemini API key

Edit the `.env` file:

```
GEMINI_API_KEY=your_actual_gemini_key_here
FLASK_SECRET_KEY=any_random_string
```

Get a free key at: https://aistudio.google.com/app/apikey

### 3. Start the server

```bash
python app.py
```

### 4. Open in browser

```
http://localhost:5000
```

---

## Supported Languages

| Language | Extensions | Chunking Method |
|---|---|---|
| Python | `.py` | `def` / `class` blocks |
| Java | `.java` | Class and method boundaries |
| COBOL | `.cbl` `.cob` `.cpy` | DIVISION / SECTION splits |
| JavaScript | `.js` | Blank-line bounded blocks |
| TypeScript | `.ts` | Blank-line bounded blocks |
| C / C++ | `.c` `.cpp` | Blank-line bounded blocks |
| Go | `.go` | Blank-line bounded blocks |

---

## AI Models Available

| Model | Speed | Quality |
|---|---|---|
| Gemini 2.5 Flash ⭐ | Fast | Great (recommended) |
| Gemini 2.0 Flash | Fast | Good |
| Gemini 2.5 Pro | Slower | Best |

---

## Tech Stack

- **Backend** — Python, Flask
- **AI** — Google Gemini via `google-generativeai` SDK
- **Frontend** — HTML5, Bootstrap 5, Highlight.js
- **Diff** — Python `difflib`
- **Styling** — Custom dark glassmorphism CSS

---

## Screenshots

> Add screenshots here after running the app

---

*Built for hackathons, college submissions, and placement portfolios.*
