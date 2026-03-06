from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Lead
from schemas import LeadCreate
from config import settings

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def homepage(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "config": settings})


@router.post("/leads", status_code=201)
def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    db_lead = Lead(
        name=lead.name,
        email=lead.email,
        company=lead.company,
        agent_description=lead.agent_description,
    )
    db.add(db_lead)
    db.commit()
    return {"ok": True}
