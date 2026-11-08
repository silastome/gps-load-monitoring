"""
===============================================================================
TESTES AUTOMATIZADOS DE INGESTÃO E VALIDAÇÃO CSV (tests/test_upload.py)
===============================================================================
"""

import os
import sqlite3
from services.upload_service import processar_csv_upload

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def init_test_db(db_path: str):
    """Inicializa a base de dados temporária garantindo a criação direta de todas as tabelas."""
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS jogadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE,
            nome_real TEXT UNIQUE,
            codigo_anonimo TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            data_sessao TEXT,
            tipo TEXT,
            tipo_sessao TEXT,
            UNIQUE(data, tipo)
        );
        CREATE TABLE IF NOT EXISTS registos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER NOT NULL,
            sessao_id INTEGER NOT NULL,
            date TEXT,
            player_name TEXT,
            duration_secs REAL,
            distance_m REAL,
            distancia_m REAL,
            player_load REAL,
            top_speed_kmh REAL,
            max_acceleration REAL,
            max_deceleration REAL,
            duration_min REAL,
            duracao_min REAL,
            distance_per_min REAL,
            distancia_per_min REAL,
            pl_per_min REAL,
            microcycle_day TEXT,
            week_id TEXT,
            iso_tuple TEXT,
            ano_iso INTEGER,
            semana_iso INTEGER,
            acute REAL,
            chronic REAL,
            acwr REAL,
            acwr_zone TEXT,
            percent_vmax REAL,
            carga_total_semanal REAL,
            monotony_player_load REAL,
            strain_player_load REAL,
            hsr_m REAL,
            sprint_m REAL,
            hsr_per_min REAL,
            sprint_per_min REAL,
            acc_count REAL,
            dec_count REAL,
            vmax_individual_p95 REAL,
            rsei_individual REAL,
            rsei REAL,
            cluster INTEGER,
            perfil_carga TEXT,
            periodo TEXT,
            ietj REAL,
            FOREIGN KEY (jogador_id) REFERENCES jogadores(id),
            FOREIGN KEY (sessao_id) REFERENCES sessoes(id),
            UNIQUE(jogador_id, sessao_id)
        );
    """)

    conn.commit()
    conn.close()


def test_importacao_csv_valido(tmp_path):
    """Testa a ingestão e validação bem-sucedida de um CSV com dados válidos."""
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
    """Testa a rejeição de ficheiros CSV com colunas obrigatórias ausentes."""
    db_temp = str(tmp_path / "test_app.db")
    init_test_db(db_temp)

    csv_invalido = b"date,player_name\n2025-07-23,Atleta 01\n"
    res = processar_csv_upload(csv_invalido, db_path=db_temp)
    assert res["sucesso"] is False


def test_rejeitar_metricas_negativas(tmp_path):
    """Testa a rejeição de registos contendo métricas com valores negativos."""
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
    """Testa o bloqueio de duplicados ao reimportar o mesmo ficheiro CSV."""
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
    