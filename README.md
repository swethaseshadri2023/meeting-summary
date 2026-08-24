# Meeting Summarizer

Transcribe meeting audio and generate action-oriented summaries: transcript → summary → key decisions → action items.

## How it works

```
 audio file
     │
     ▼
 ┌─────────────┐      ┌──────────────────┐      ┌───────────────┐
 │ Transcriber │ ───▶ │   Summarizer      │ ───▶ │  SQLite store  │
 │ (ASR)       │      │  (Claude LLM)     │      │                │
 └─────────────┘      └──────────────────┘      └───────────────┘
        │                                              │
        ▼                                              ▼
   faster-whisper                                 FastAPI JSON API
   or OpenAI Whisper                                    │
                                                          ▼
                                                  index.html frontend
```

- **ASR**: `faster-whisper` runs locally by default (no API key, works offline). Swap to the OpenAI Whisper API by setting `ASR_PROVIDER=openai`. Adding Google Speech-to-Text or Azure Speech is a matter of writing one more `_transcribe_with_x()` function in `backend/transcriber.py`.
- **LLM**: Anthropic's Claude summarizes the transcript into a JSON object (summary, key decisions, action items) using a strict-JSON system prompt, so the output is reliably parseable.
- **Backend**: FastAPI + SQLite. One endpoint accepts an audio upload and returns the full result synchronously; separate endpoints list/fetch/delete past meetings.
- **Frontend**: a single static `index.html` (no build step) that uploads audio, shows a processing state, and renders the summary, decisions, and action items, plus history of past runs.

## Project structure

```
meeting-summarizer/
├── backend/
│   ├── main.py          FastAPI app & routes
│   ├── transcriber.py   ASR (faster-whisper / OpenAI Whisper)
│   ├── summarizer.py    Claude prompt + JSON parsing
│   ├── database.py      SQLite persistence
│   ├── models.py        Pydantic response models
│   ├── config.py        Env var config
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html       Upload UI + results viewer
└── README.md
```

## Setup

### 1. Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`faster-whisper` will download the selected Whisper model (see `WHISPER_MODEL_SIZE`) the first time it runs.

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...     # required, from console.anthropic.com
CLAUDE_MODEL=claude-sonnet-4-6

ASR_PROVIDER=local               # or "openai"
WHISPER_MODEL_SIZE=small         # tiny/base/small/medium/large-v3
OPENAI_API_KEY=                  # only needed if ASR_PROVIDER=openai
```

### 3. Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** — FastAPI serves the frontend directly, so there's nothing else to start. The API itself lives under `/api/*` (e.g. `http://localhost:8000/api/health`).

## API reference

| Method | Path                    | Description                                  |
|--------|--------------------------|-----------------------------------------------|
| POST   | `/api/meetings`          | Upload audio (`multipart/form-data`, field `file`). Returns full result. |
| GET    | `/api/meetings`          | List past meetings (id, filename, status, timestamps). |
| GET    | `/api/meetings/{id}`     | Full detail: transcript, summary, decisions, action items. |
| DELETE | `/api/meetings/{id}`     | Delete a meeting record.                     |
| GET    | `/api/health`            | Liveness check.                              |

Example:

```bash
curl -X POST http://localhost:8000/api/meetings \
  -F "file=@team_standup.mp3"
```

Response:

```json
{
  "id": 1,
  "filename": "team_standup.mp3",
  "status": "done",
  "transcript": "…full transcript…",
  "summary": "The team reviewed sprint progress and agreed to delay the release by one week to finish QA.",
  "key_decisions": ["Delay release by one week", "Move QA sign-off to Friday"],
  "action_items": [
    {"owner": "Priya", "task": "Finish regression test suite", "due_date": "Friday"},
    {"owner": "Unassigned", "task": "Update release notes", "due_date": "Not specified"}
  ],
  "created_at": "2026-08-24T10:02:11.123Z",
  "updated_at": "2026-08-24T10:02:47.981Z"
}
```

## The core LLM prompt

`backend/summarizer.py` sends the transcript with a system prompt instructing Claude to return only JSON in a fixed shape (`summary`, `key_decisions`, `action_items`), based directly on the brief's example prompt ("Summarize this meeting transcript into key decisions and action items."). Strict JSON output means the API never has to guess at parsing free-form text.

## Notes on evaluation criteria

- **Transcription accuracy**: `faster-whisper` with `vad_filter=True` trims silence/noise before transcribing; model size is configurable to trade speed for accuracy.
- **Summary quality**: the prompt constrains the model to only use transcript content (no hallucinated facts) and requires specific, actionable task descriptions.
- **Prompt effectiveness**: JSON-only output with explicit schema and fallback parsing (`summarizer.py::_extract_json`) means malformed LLM output degrades gracefully instead of crashing the API.
- **Code structure**: ASR, LLM, storage, and API layers are fully decoupled — each can be swapped (e.g. Azure Speech instead of Whisper, GPT instead of Claude) by editing one file.

## Deliverables checklist

- [x] GitHub repo layout + this README
- [ ] Demo video — record a short walkthrough: upload a sample audio file, show the processing state, then the rendered summary/decisions/action items and history list.
