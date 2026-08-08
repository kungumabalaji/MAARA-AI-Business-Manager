from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.connection import SessionLocal

app = FastAPI(title="MAARA AI Business Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def login(payload: LoginRequest):
    db = SessionLocal()
    try:
        # Placeholder auth flow. Replace this with your real Supabase auth integration later.
        if payload.email and payload.password:
            return {
                "message": "Login successful",
                "access_token": "demo-token",
                "refresh_token": "demo-refresh-token",
                "user": {"email": payload.email},
            }
        return {"message": "Invalid credentials"}, 400
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
