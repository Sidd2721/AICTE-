import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg

# Load .env from project root or current directory
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")
load_dotenv()

def create_roles():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        sys.stderr.write("Error: DATABASE_URL environment variable is not set.\n")
        sys.exit(1)
    # Ensure scheme is psycopg compatible
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)
    conn = psycopg.connect(db_url)
    with conn.cursor() as cur:
        # Check and create migrator
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'migrator'")
        if not cur.fetchone():
            cur.execute("CREATE ROLE migrator WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
            print("Role 'migrator' created.")
        else:
            print("Role 'migrator' already exists.")

        # Check and create app
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'app'")
        if not cur.fetchone():
            cur.execute("CREATE ROLE app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS")
            print("Role 'app' created.")
        else:
            print("Role 'app' already exists.")

        # Grant roles to postgres superuser so postgres can alter default privileges on their behalf
        cur.execute("GRANT migrator TO postgres")
        cur.execute("GRANT app TO postgres")
        print("Granted migrator and app membership to postgres.")
            
        conn.commit()
    conn.close()

if __name__ == "__main__":
    create_roles()
