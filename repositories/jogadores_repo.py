from repositories import get_connection

def get_todos_jogadores():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jogadores")
        return [dict(r) for r in cursor.fetchall()]
