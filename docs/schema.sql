-- Script DDL de Criação do Esquema Relacional (3FN) - SQLite3

CREATE TABLE IF NOT EXISTS jogadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL,
    posicao TEXT
);

CREATE TABLE IF NOT EXISTS sessoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    tipo TEXT
);

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
