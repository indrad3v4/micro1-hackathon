# Creative Court 2.0 — Black Box Unveiled Dashboard

A Reflex.dev frontend dashboard for the Creative Court 2.0 pipeline.
Three-panel layout with brief input, generated directions (the Arena), and a real-time trace log feed.

## Quick Start

```bash
cd cc-app
reflex run
```

The app starts at `http://localhost:3000/` by default (ports may shift if in use).

## Prerequisites

- Python 3.12+
- Node.js 20+ (for the Reflex dev server)
- uv or pip (to install dependencies)

## Dependencies

```
reflex==0.9.9
pydantic>=2.10.0
openai>=1.0.0
fastapi>=0.115.0
```

Install with:

```bash
uv pip install -r requirements.txt --python .venv/bin/python
```

## Architecture

### Three-Panel Layout

| Panel | Description |
|-------|-------------|
| **Left** | Brief input form — title, description, audience, constraints, creativity slider |
| **Center** | The Arena — direction cards with color-coded scores (green >60, red <60) and Veto buttons |
| **Right** | Terminal-style trace log showing TraceRecorder events in real time |

### State Schema

`CCState` manages all dashboard state:

- **Brief fields**: `title`, `description`, `audience`, `constraints_raw`, `creativity`
- **Directions**: 6 individual fields (`direction_0_*` through `direction_5_*`) covering all IKRA frames
- **Orchestration**: `is_running`, `max_retries`, `retry_count`, `retry_needed`, `all_approved`
- **Trace log**: `trace_log` (list of dicts), `_trace_lines` (display strings), `trace_path`
- **Results**: `num_directions`, `verdicts`

### Pipeline Orchestration

1. `handle_submit()` initializes CreatorAgent and JudgeAgent
2. Calls `Creator.generate(brief)` to produce creative directions across IKRA frames
3. Calls `Judge.judge(brief, directions)` to score each direction on relevance, novelty, feasibility, risk, quality
4. Loops until all directions are approved (score >= 60) or max retries reached
5. Each step emits trace events to the JSONL trajectory file

### Veto Workflow

Clicking "Veto & Redo" on any card calls `handle_veto(frame_name)` which regenerates that frame's direction while keeping others intact. The new generation addresses concerns from the previous iteration.

### Export

The "Export Trace Artifact" button creates a ZIP containing:
- `creative-court-results.json` — full session data (brief, directions, verdicts, trace log)
- Any `.jsonl` trace files from the traces directory

## Project Structure

```
cc-app/
├── rxconfig.py            # Reflex configuration (RadixThemesPlugin, TailwindV4, Sitemap)
├── requirements.txt       # Python dependencies
├── cc_app/
│   ├── __init__.py
│   ├── cc_app.py          # Main application code
│   └── creative_court/    # Inline agent modules (self-contained copy)
│       ├── __init__.py
│       ├── core/
│       │   ├── models.py   # Brief, Direction, Verdict, TraceEvent
│       │   ├── trace.py    # TraceRecorder (append-only JSONL)
│       │   └── llm.py      # LLMClient + heuristic fallback
│       └── agents/
│           ├── creator.py  # CreatorAgent -> generate directions
│           └── judge.py    # JudgeAgent -> score on rubric
├── traces/                # Generated trajectory JSONL files
└── README.md
```

## Design

- Dark mode professional UI using Radix Themes plugin
- Split-screen responsive layout with three columns
- Color-coded direction cards: green border for approved (score >= 60), red for rejected
- Terminal-style trace log with monospace font and timestamp formatting
- All code and comments in English
