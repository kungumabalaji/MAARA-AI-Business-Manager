import os
from urllib.parse import quote, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))


def read_database_url() -> str | None:
    raw_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_URL")
        or os.getenv("SUPABASE_DATABASE_URL")
    )

    if raw_url:
        return raw_url

    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return None

    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key in {"DATABASE_URL", "SUPABASE_URL", "SUPABASE_DATABASE_URL"} and value:
                    return value

            if line.startswith("postgres://") or line.startswith("postgresql://"):
                return line

    return None


def normalize_database_url(raw_url: str) -> str:
    if not raw_url:
        return raw_url

    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if not url.startswith("postgresql://"):
        return raw_url

    parsed = urlsplit(url)
    username = quote(parsed.username or "", safe="")
    password = quote(parsed.password or "", safe="")

    netloc = parsed.hostname or ""
    if username or password:
        netloc = f"{username}:{password}@{netloc}"

    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    query = parsed.query
    if "sslmode=" not in query:
        query = f"{query}&sslmode=require" if query else "sslmode=require"

    return urlunsplit(
        ("postgresql+psycopg", netloc, parsed.path or "/postgres", query, parsed.fragment)
    )


DATABASE_URL = read_database_url()

if not DATABASE_URL:
    raise ValueError(
        "No database URL found. Set DATABASE_URL or SUPABASE_URL in your .env file"
    )

DATABASE_URL = normalize_database_url(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()