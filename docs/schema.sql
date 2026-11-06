-- Script DDL de Criação do Esquema Relacional (3FN) - SQLite3
-- Projeto: gps-load-monitoring

PRAGMA foreign_keys = ON;

-- 1. Dimensão de Atletas (Anonimizados)
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synthetic_code TEXT UNIQUE NOT NULL,
    original_name_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Dimensão de Sessões de Treino
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date DATE NOT NULL,
    microcycle_day TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_date, microcycle_day)
);

-- 3. Tabela de Fatos / Telemetria GPS
CREATE TABLE IF NOT EXISTS gps_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    duration_min REAL NOT NULL CHECK(duration_min >= 0),
    distance_m REAL NOT NULL CHECK(distance_m >= 0),
    player_load REAL NOT NULL CHECK(player_load >= 0),
    top_speed_kmh REAL NOT NULL CHECK(top_speed_kmh >= 0),
    hsr_m REAL DEFAULT 0 CHECK(hsr_m >= 0),
    acc_count REAL DEFAULT 0 CHECK(acc_count >= 0),
    dec_count REAL DEFAULT 0 CHECK(dec_count >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    UNIQUE(player_id, session_id)
);

-- Índices de Desempenho para Consultas Analíticas
CREATE INDEX IF NOT EXISTS idx_gps_records_player ON gps_records(player_id);
CREATE INDEX IF NOT EXISTS idx_gps_records_session ON gps_records(session_id);