from fastapi import APIRouter

from app.api.routes import (
    audit,
    dashboard,
    deposits,
    documents,
    evidence,
    fraud_lab,
    instruments,
    integration,
    integration_v1,
    login,
    meta,
    private,
    release,
    reports,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(meta.router)
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(audit.router)
api_router.include_router(deposits.router)
api_router.include_router(documents.router)
api_router.include_router(instruments.router)
api_router.include_router(release.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(fraud_lab.router)
api_router.include_router(evidence.router)
api_router.include_router(integration.router)
api_router.include_router(integration_v1.keys_router)


if settings.FASTAPI_ENV in ("development", "demo"):
    api_router.include_router(private.router)
