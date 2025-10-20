# ...existing code...
from sqlalchemy import create_engine, text
from app.config import settings

url = settings.DATABASE_URL
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

print("Usando URL:", url)
# { changed code } only pass sslmode when using postgres
connect_args = {"sslmode": "require"} if url.startswith("postgresql") else {}
engine = create_engine(url, connect_args=connect_args)
try:
    with engine.connect() as conn:
        r = conn.execute(text("SELECT 1"))
        print("Conexión OK, resultado:", list(r))
except Exception as e:
    print("ERROR de conexión:", e)
# ...existing code...