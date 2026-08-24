"""
Meeting Summarizer API
=======================
Endpoints:
  POST /api/meetings           Upload an audio file -> transcribe + summarize (sync)
  GET  /api/meetings           List past meetings
  GET  /api/meetings/{id}      Get full detail (transcript, summary, action items)
  DELETE /api/meetings/{id}    Delete a meeting record + its audio file

Run with:  uvicorn main:app --reload --port 8000
"""
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import database as db
from config import UPLOAD_DIR, MAX_UPLOAD_MB, ALLOWED_AUDIO_EXTENSIONS
from transcriber import transcribe_audio
from summarizer import summarize_transcript
from models import MeetingDetail, MeetingListItem

app = FastAPI(title="Meeting Summarizer API", version="1.0.0")

# Allow the frontend (served separately, e.g. on a different port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db.init_db()


@app.post("/api/meetings", response_model=MeetingDetail)
async def upload_and_process(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_AUDIO_EXTENSIONS)}",
        )

    # Save upload to disk under a unique name (avoid collisions / path issues).
    dest_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    with dest_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    size_mb = dest_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(400, f"File too large ({size_mb:.1f} MB). Max is {MAX_UPLOAD_MB} MB.")

    meeting_id = db.create_meeting(filename=file.filename)

    try:
        transcript = transcribe_audio(dest_path)
        result = summarize_transcript(transcript)
        db.mark_done(
            meeting_id,
            transcript=transcript,
            summary=result["summary"],
            key_decisions=result["key_decisions"],
            action_items=result["action_items"],
        )
    except Exception as e:  # noqa: BLE001 - surface any pipeline error to the caller
        db.mark_failed(meeting_id, str(e))
        raise HTTPException(500, f"Processing failed: {e}") from e
    finally:
        # Keep the audio file only if you want to allow re-processing later;
        # deleting it here saves disk space. Comment out to retain audio.
        dest_path.unlink(missing_ok=True)

    return db.get_meeting(meeting_id)


@app.get("/api/meetings", response_model=list[MeetingListItem])
def list_meetings(limit: int = 50):
    return db.list_meetings(limit=limit)


@app.get("/api/meetings/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: int):
    meeting = db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    return meeting


@app.delete("/api/meetings/{meeting_id}")
def delete_meeting(meeting_id: int):
    meeting = db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    with db.get_conn() as conn:
        conn.execute("DELETE FROM meetings WHERE id=?", (meeting_id,))
    return {"deleted": meeting_id}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve the simple frontend (index.html + JS) directly from FastAPI so the
# whole app can run from a single process during a demo.
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
