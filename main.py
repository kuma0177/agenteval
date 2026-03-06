from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from database import Base, engine
from routers import public, client, reviewer, admin, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AgentEval", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(public.router)
app.include_router(client.router)
app.include_router(reviewer.router)
app.include_router(admin.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"status": "ok"}
