#!/bin/sh
set -e

echo "==> Waiting for database..."
python -c "
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def wait():
    url = os.environ.get('DATABASE_URL')
    for i in range(60):
        try:
            engine = create_async_engine(url)
            async with engine.connect() as conn:
                await conn.execute(text('SELECT 1'))
            await engine.dispose()
            print('database is ready')
            return
        except Exception:
            await asyncio.sleep(2)
    raise SystemExit('database not reachable')

asyncio.run(wait())
"

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Ensuring initial admin (only when ADMIN_PASSWORD is set)..."
if [ -n "${ADMIN_PASSWORD}" ]; then
    python -m app.create_admin || true
else
    echo "ADMIN_PASSWORD not set - skipping admin bootstrap."
fi

echo "==> Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
