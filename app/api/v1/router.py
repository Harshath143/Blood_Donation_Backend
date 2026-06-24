from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, users, donors, blood_requests, donations, blood_banks, websocket

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(donors.router, prefix="/donors", tags=["donors"])
api_router.include_router(blood_requests.router, prefix="/requests", tags=["blood-requests"])
api_router.include_router(donations.router, prefix="/donations", tags=["donations"])
api_router.include_router(blood_banks.router, prefix="/blood-banks", tags=["blood-banks"])
api_router.include_router(websocket.router, tags=["websocket"])
