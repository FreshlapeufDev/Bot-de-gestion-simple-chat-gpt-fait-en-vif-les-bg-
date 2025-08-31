import psycopg2

# Ta DATABASE_URL Railway (n’hésite pas à la mettre en variable d’environnement pour la sécurité)
DATABASE_URL = "postgresql://postgres:nASrGvRUAgRBEoOLRvhmZaETwMfpHkZG@postgres.railway.internal:5432/railway"

# Connexion à la base PostgreSQL
conn = psycopg2.connect(DATABASE_URL)

def setup_table():
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                user_id TEXT PRIMARY KEY,
                invite_count INT DEFAULT 0
            );
        """)
        conn.commit()

def add_invitation(user_id):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO invitations (user_id, invite_count)
            VALUES (%s, 1)
            ON CONFLICT (user_id) DO UPDATE SET invite_count = invitations.invite_count + 1;
        """, (str(user_id),))
        conn.commit()

def get_invitation_count(user_id):
    with conn.cursor() as cur:
        cur.execute("SELECT invite_count FROM invitations WHERE user_id = %s;", (str(user_id),))
        result = cur.fetchone()
        return result[0] if result else 0

def get_top_inviters(limit=10):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT user_id, invite_count FROM invitations
            ORDER BY invite_count DESC
            LIMIT %s;
        """, (limit,))
        return cur.fetchall()

# Crée la table automatiquement au démarrage
setup_table()
