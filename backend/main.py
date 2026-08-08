from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.auth import router as auth_router
from api.v1.daily_reports import router as daily_reports_router
from api.v1.dashboards import router as dashboards_router
from api.v1.report_templates import router as report_templates_router
from core.config import get_settings

app = FastAPI(title="MAARA AI Business Manager")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
