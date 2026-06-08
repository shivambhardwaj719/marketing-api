from fastapi import APIRouter
from .analytics.routes import router as analytics_router
from .auth.routes import router as auth_router
from .campaigns.routes import router as campaigns_router
from .facebook.routes import router as facebook_router
from .instagram.routes import router as instagram_router
from .leads.routes import router as leads_router
from .webhooks.routes import router as webhooks_router
from .whatsapp.routes import router as whatsapp_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(facebook_router)
api_v1_router.include_router(campaigns_router)
api_v1_router.include_router(instagram_router)
api_v1_router.include_router(leads_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(whatsapp_router)
