import psycopg

def set_ownership_to_migrator():
    conn = psycopg.connect("host=localhost port=5432 dbname=app user=postgres password=changethis", autocommit=True)
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    tables = [row[0] for row in cur.fetchall()]
    for t in tables:
        cur.execute(f'ALTER TABLE public."{t}" OWNER TO migrator;')
        cur.execute(f'GRANT ALL ON TABLE public."{t}" TO migrator;')
        cur.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public."{t}" TO app;')
    
    cur.execute("SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public'")
    seqs = [row[0] for row in cur.fetchall()]
    for s in seqs:
        cur.execute(f'ALTER SEQUENCE public."{s}" OWNER TO migrator;')
        cur.execute(f'GRANT ALL ON SEQUENCE public."{s}" TO migrator;')
        cur.execute(f'GRANT USAGE, SELECT ON SEQUENCE public."{s}" TO app;')
        
    conn.close()
    print(f"Ownership of {len(tables)} tables and {len(seqs)} sequences successfully transferred to migrator.")

if __name__ == "__main__":
    set_ownership_to_migrator()
