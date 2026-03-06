from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from config import settings
from database import Base, engine
from routers import public, client, reviewer, admin, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AgentEval", lifespan=lifespan)
_templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(public.router)
app.include_router(client.router)
app.include_router(reviewer.router)
app.include_router(admin.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return _templates.TemplateResponse(
        "404.html", {"request": request, "config": settings}, status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    return _templates.TemplateResponse(
        "500.html", {"request": request, "config": settings}, status_code=500
    )
