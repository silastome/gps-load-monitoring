-- ============================================================
-- UFCD 5425 — Sistema de Monitorização de Carga Externa (IEFP)
-- Schema SQLite Normalizado (3 Tabelas)
-- ============================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jogadores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo     TEXT NOT NULL UNIQUE,
    nome       TEXT NOT NULL,
    posicao    TEXT DEFAULT 'Plantel Principal',
    criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessoes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    data              TEXT NOT NULL UNIQUE,
    fase_microciclo   TEXT NOT NULL,
    week_id           TEXT,
    iso_tuple         TEXT,
    ano_iso           INTEGER,
    semana_iso        INTEGER,
    periodo           TEXT,
    criado_em         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registos (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    jogador_id           INTEGER NOT NULL,
    sessao_id            INTEGER NOT NULL,
    
    -- Volume
    duration_secs        REAL,
    duration_min         REAL,
    distance_m           REAL,
    player_load          REAL,
    
    -- Intensidade
    top_speed_kmh        REAL,
    max_acceleration     REAL,
    max_deceleration     REAL,
    percent_vmax         REAL,
    
    -- Densidades
    distance_per_min     REAL,
    pl_per_min            REAL,
    hsr_m                REAL,
    sprint_m             REAL,
    hsr_per_min          REAL,
    sprint_per_min       REAL,
    
    -- ACWR
    acute                REAL,
    chronic              REAL,
    acwr                 REAL,
    acwr_zone            TEXT,
    
    -- Foster / Monotonia / Strain
    carga_total_semanal  REAL,
    monotony_player_load REAL,
    strain_player_load   REAL,
    
    -- Neuromuscular / Índices
    vmax_individual_p95  REAL,
    rsei_global_old      REAL,
    rsei_individual      REAL,
    ietj                 REAL,
    
    -- Clustering
    cluster              INTEGER,
    perfil_carga         TEXT,
    
    FOREIGN KEY (jogador_id) REFERENCES jogadores(id) ON DELETE CASCADE,
    FOREIGN KEY (sessao_id)  REFERENCES sessoes(id)  ON DELETE CASCADE,
    UNIQUE(jogador_id, sessao_id)
);

CREATE INDEX IF NOT EXISTS idx_registos_jogador   ON registos(jogador_id);
CREATE INDEX IF NOT EXISTS idx_registos_sessao    ON registos(sessao_id);
CREATE INDEX IF NOT EXISTS idx_registos_acwr_zone ON registos(acwr_zone);
CREATE INDEX IF NOT EXISTS idx_sessoes_fase       ON sessoes(fase_microciclo);
CREATE INDEX IF NOT EXISTS idx_sessoes_data       ON sessoes(data);
