"""Sign in with Google (Emergent-managed) for existing vendor and staff accounts only."""
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from routers._social_signin import sign_in_existing

router = APIRouter(prefix="/api/v1/auth/google", tags=["google-auth"])
SESSION_DATA_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


class ExchangeIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=512)
    portal: Literal["supplier", "staff", "admin"]


async def _google_email(session_id: str) -> str:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(SESSION_DATA_URL, headers={"X-Session-ID": session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified. Please try again.")
    email = (r.json().get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="Google did not share an email address.")
    return email


@router.post("/exchange")
async def exchange(body: ExchangeIn, response: Response, request: Request):
    email = await _google_email(body.session_id)
    return await sign_in_existing(email, body.portal, response, request, "google")
