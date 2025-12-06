from ast import parse
from fastapi import APIRouter

from app.api.endpoints import auth, chats, messages, health, analyze, parse_document, folders, business, calendar, onboarding, wb


api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(chats.router)
api_router.include_router(messages.router)
api_router.include_router(analyze.router)
api_router.include_router(parse_document.router)
api_router.include_router(folders.router)
api_router.include_router(business.router)
api_router.include_router(calendar.router)
api_router.include_router(onboarding.router)
api_router.include_router(wb.router)
