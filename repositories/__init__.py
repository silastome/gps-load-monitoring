import sqlite3
import os

DB_PATH = "app.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jogadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            posicao TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            tipo TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER,
            sessao_id INTEGER,
            microcycle_day TEXT,
            duration_min REAL,
            distancia_m REAL,
            distance_per_min REAL,
            player_load REAL,
            top_speed_kmh REAL,
            hsr_m REAL,
            acc_count REAL,
            dec_count REAL,
            ietj REAL,
            rsei REAL,
            FOREIGN KEY(jogador_id) REFERENCES jogadores(id),
            FOREIGN KEY(sessao_id) REFERENCES sessoes(id)
        );
    """)
    conn.commit()
    conn.close()

def reset_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()

# Inicializa as tabelas na primeira execução
init_db()