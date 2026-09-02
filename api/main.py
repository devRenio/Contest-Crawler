from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from collector.config import settings
from collector.store import add_submission, init_db, list_contests

app = FastAPI(title="Contest Crawler API", version="0.1.0")
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SubmissionIn(BaseModel):
    title: str
    url: HttpUrl
    organizer: str = ""
    note: str = ""


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/v1/contests")
def contests(
    tab: str = Query("all", pattern="^(all|new|closing)$"),
    tag: str = "",
    q: str = "",
):
    items = list_contests(tab=tab, tag=tag, q=q)
    return {"tab": tab, "count": len(items), "items": [i.model_dump() for i in items]}


@app.post("/v1/submissions")
def submit(body: SubmissionIn) -> dict:
    add_submission(body.title, body.organizer, str(body.url), body.note)
    return {"ok": True}
