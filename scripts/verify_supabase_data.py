import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg

# Load .env from project root or current directory
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")
load_dotenv()

def verify():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        sys.stderr.write("Error: DATABASE_URL environment variable is not set.\n")
        sys.exit(1)
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
    conn = psycopg.connect(db_url)
    with conn.cursor() as cur:
        for t in ["user", "institution", "instrument", "confirmation", "obligation", "audit_event"]:
            cur.execute(f'SELECT count(*) FROM "{t}"')
            print(f"Table '{t}': {cur.fetchone()[0]} rows")
        cur.execute("SELECT audit_verify()")
        print(f"Cryptographic Audit Continuity: {cur.fetchone()[0]} (None means 100% verified intact)")
    conn.close()

if __name__ == "__main__":
    verify()
