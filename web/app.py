from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from api.main import app as api_app


web_app = FastAPI(title="ASTRA Web Control Center", version="0.1.0")
templates = Jinja2Templates(directory="web/templates")


@web_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


web_app.mount("/static", StaticFiles(directory="web/static"), name="static")
web_app.mount("/api", api_app)
