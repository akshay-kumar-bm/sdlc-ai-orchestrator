import os

# Set required env vars before any app module is imported
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/aeo_test")
