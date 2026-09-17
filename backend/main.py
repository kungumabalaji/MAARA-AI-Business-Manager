import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.auth import router as auth_router
from api.v1.daily_reports import router as daily_reports_router
from api.v1.dashboards import router as dashboards_router
from api.v1.report_templates import router as report_templates_router
from core.config import get_settings

# Without this, module loggers (services.vision_service, api.v1.*, ...) never
# print anything below WARNING, so the terminal only shows uvicorn's bare
# "METHOD path STATUS" access log lines with no context for *why* a request failed.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="MAARA AI Business Manager")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Vercel mints a fresh random hostname for every deployment/preview
    # (e.g. maara-ai-business-manager-4e8ppq9gt.vercel.app) — matching those
    # by pattern means CORS keeps working without editing CORS_ALLOW_ORIGINS
    # on every deploy.
    allow_origin_regex=r"^https://maara-ai-busine[\w-]*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(report_templates_router)
app.include_router(daily_reports_router)
app.include_router(dashboards_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
