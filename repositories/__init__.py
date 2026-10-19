import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jogadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                posicao TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                tipo TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jogador_id INTEGER,
                sessao_id INTEGER,
                distancia_m REAL,
                player_load REAL,
                top_speed_kmh REAL,
                FOREIGN KEY(jogador_id) REFERENCES jogadores(id),
                FOREIGN KEY(sessao_id) REFERENCES sessoes(id)
            )
        ''')
        conn.commit()
