"""The HTTP service.

It never writes the text it is given anywhere: not to disk, not to the logs. The only thing it
remembers, in memory, is the address and time of recent requests, which the rate limit
counts. The demo page and the browser extension do not use it - they carry the model - so it
is for restoring text from code.
"""

from __future__ import annotations

import time
from collections import deque
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from schwa import __version__
from schwa.changes import changes_between

from schwa_api.restorers import Loaded, load_restorer

MAX_CHARACTERS = 10_000
REQUESTS_PER_MINUTE = 60

app = FastAPI(
    title="schwa",
    version=__version__,
    summary="Restore Azerbaijani diacritics in text typed without them",
)

# The web page and the extension are served from other origins, and the extension's origin
# is a chrome-extension:// URL that cannot be listed in advance. No credentials are ever
# involved, so an open policy costs nothing here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class RestoreRequest(BaseModel):
    text: str = Field(max_length=MAX_CHARACTERS, description="text as it was typed")


class ChangeOut(BaseModel):
    start: int
    end: int
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class RestoreResponse(BaseModel):
    text: str
    changes: list[ChangeOut]


class InfoResponse(BaseModel):
    version: str
    restorer: str
    sources: dict[str, str]
    max_characters: int
    stores_text: bool = False


@lru_cache(maxsize=1)
def get_restorer() -> Loaded:
    """Load the restorer once and keep it for the life of the process."""
    return load_restorer()


class RateLimiter:
    """A small per-address limit, enough for one instance behind one demo page."""

    def __init__(self, allowance: int = REQUESTS_PER_MINUTE, window: float = 60.0) -> None:
        self.allowance = allowance
        self.window = window
        self._seen: dict[str, deque[float]] = {}

    def check(self, address: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        recent = self._seen.setdefault(address, deque())
        while recent and moment - recent[0] > self.window:
            recent.popleft()
        if len(recent) >= self.allowance:
            return False
        recent.append(moment)
        return True


limiter = RateLimiter()


@app.post("/v1/restore", response_model=RestoreResponse)
def restore(
    request: RestoreRequest,
    http_request: Request,
    loaded: Loaded = Depends(get_restorer),
) -> RestoreResponse:
    """Restore the diacritics and report every word that changed."""
    address = http_request.client.host if http_request.client else "unknown"
    if not limiter.check(address):
        raise HTTPException(status_code=429, detail="too many requests")

    restored = loaded.restorer.restore(request.text)
    changes = [ChangeOut(**change.as_dict()) for change in changes_between(request.text, restored)]
    return RestoreResponse(text=restored, changes=changes)


@app.get("/v1/info", response_model=InfoResponse)
def info(loaded: Loaded = Depends(get_restorer)) -> InfoResponse:
    """What this instance is actually running."""
    return InfoResponse(
        version=__version__,
        restorer=loaded.name,
        sources=loaded.sources,
        max_characters=MAX_CHARACTERS,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
