"""
===============================================================================
TESTES AUTOMATIZADOS DE INGESTÃO E VALIDAÇÃO CSV (tests/test_upload.py)
===============================================================================
"""

import os
import sqlite3
import pytest
from services.upload_service import processar_csv_upload

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def init_test_db(db_path: str):
    """Inicializa a base de dados temporária usando o schema.sql oficial do projeto."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tenta ler o esquema oficial em docs/schema.sql
    schema_paths = [
        os.path.join(BASE_DIR, "docs", "schema.sql"),
        os.path.join(BASE_DIR, "schema.sql"),
    ]
    schema_carregado = False
    for path in schema_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                cursor.executescript(f.read())
            schema_carregado = True
            break

    # Fallback com todas as variações de colunas caso o ficheiro não seja encontrado
    if not schema_carregado:
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS jogadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                nome_real TEXT UNIQUE,
                codigo_anonimo TEXT UNIQUE
            );
            CREATE TABLE IF NOT EXISTS sessoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                data_sessao TEXT,
                tipo TEXT,
                tipo_sessao TEXT
            );
            CREATE TABLE IF NOT EXISTS registos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jogador_id INTEGER NOT NULL,
                sessao_id INTEGER NOT NULL,
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
                FOREIGN KEY (jogador_id) REFERENCES jogadores(id),
                FOREIGN KEY (sessao_id) REFERENCES sessoes(id),
                UNIQUE(jogador_id, sessao_id)
            );
        """)

    conn.commit()
    conn.close()


def test_importacao_csv_valido(tmp_path):
    db_temp = str(tmp_path / "test_app.db")
    init_test_db(db_temp)

    csv_conteudo = (
        b"date,player_name,distance_m,duration_min,player_load,top_speed_kmh\n"
        b"2025-07-23,Atleta 01,5200.0,90.0,240.5,29.8\n"
        b"2025-07-23,Atleta 02,4800.0,90.0,210.0,28.2\n"
    )
    res = processar_csv_upload(csv_conteudo, db_path=db_temp)
    assert res["sucesso"] is True, f"Falha no processamento: {res}"
    assert res["novos_registos"] == 2
    assert res["linhas_rejeitadas"] == 0


def test_rejeitar_colunas_ausentes(tmp_path):
    db_temp = str(tmp_path / "test_app.db")
    init_test_db(db_temp)

    csv_invalido = b"date,player_name\n2025-07-23,Atleta 01\n"
    res = processar_csv_upload(csv_invalido, db_path=db_temp)
    assert res["sucesso"] is False


def test_rejeitar_metricas_negativas(tmp_path):
    db_temp = str(tmp_path / "test_app.db")
    init_test_db(db_temp)

    csv_negativo = (
        b"date,player_name,distance_m,duration_min,player_load,top_speed_kmh\n"
        b"2025-07-23,Atleta 01,-500.0,90.0,240.5,29.8\n"
    )
    res = processar_csv_upload(csv_negativo, db_path=db_temp)
    assert res["sucesso"] is False
    assert res["novos_registos"] == 0


def test_prevenir_duplicacao(tmp_path):
    db_temp = str(tmp_path / "test_app.db")
    init_test_db(db_temp)

    csv_conteudo = (
        b"date,player_name,distance_m,duration_min,player_load,top_speed_kmh\n"
        b"2025-07-23,Atleta 01,5200.0,90.0,240.5,29.8\n"
    )
    res1 = processar_csv_upload(csv_conteudo, db_path=db_temp)
    assert res1["sucesso"] is True, f"Falha na 1a importacao: {res1}"
    assert res1["novos_registos"] == 1

    res2 = processar_csv_upload(csv_conteudo, db_path=db_temp)
    assert res2["novos_registos"] == 0
    assert res2["linhas_rejeitadas"] == 1