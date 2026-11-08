"""
===============================================================================
MÓDULO DE LEITURA E CARREGAMENTO DE DADOS PARA O DASHBOARD
===============================================================================
Descrição: Garante o carregamento robusto e seguro do conjunto de dados
           operacional (sem carregar ficheiros estáticos da tese).
===============================================================================
"""

import hashlib
import json
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "outputs")
CACHE_DIR = os.path.join(BASE_DIR, "cache")


def _sha256_curto(caminho: str, n_bytes: int = 8) -> str:
    if not os.path.exists(caminho):
        return "n/a"
    h = hashlib.sha256()
    try:
        with open(caminho, "rb") as f:
            h.update(f.read(65536))
        return h.hexdigest()[:n_bytes]
    except Exception:
        return "n/a"


def carregar_dashboard(db_path=None):
    """
    Carrega o DataFrame principal exclusivamente da base de dados operacional:
    1. outputs/conversao_dash_final.csv
    2. Base de dados SQLite (fallback)
    """
    csv_dash = os.path.join(OUT_DIR, "conversao_dash_final.csv")

    df = None
    caminho_usado = None

    if os.path.exists(csv_dash):
        caminho_usado = csv_dash
        try:
            df = pd.read_csv(csv_dash, encoding="utf-8-sig")
        except Exception:
            try:
                df = pd.read_csv(csv_dash, encoding="latin-1")
            except Exception:
                df = None

    if df is None or df.empty:
        try:
            from repositories import get_db_connection
            conn = get_db_connection(db_path)
            query = """
                SELECT r.*, j.nome as player_name, s.data as date, s.tipo as microcycle_day
                FROM registos r
                JOIN jogadores j ON r.jogador_id = j.id
                JOIN sessoes s ON r.sessao_id = s.id
            """
            df_db = pd.read_sql_query(query, conn)
            conn.close()

            if df_db is not None and not df_db.empty:
                df = df_db.copy()
                caminho_usado = "sqlite_db"
        except Exception:
            pass

    if df is None or df.empty:
        return pd.DataFrame(), {
            "csv_path": "nenhum",
            "csv_sha": "n/a",
            "csv_size_kb": 0.0,
            "qc": {},
            "alertas": ["Nenhum dado importado até ao momento."],
            "n_obs": 0,
            "n_atletas": 0,
            "n_dias": 0,
            "colunas": [],
        }

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = pd.Timestamp.today().normalize()

    n_atl = int(df["player_name"].nunique()) if "player_name" in df.columns else 0
    n_dias = int(df["date"].dt.date.nunique()) if "date" in df.columns else 0

    meta = {
        "csv_path":     caminho_usado,
        "csv_sha":      _sha256_curto(caminho_usado) if caminho_usado != "sqlite_db" else "db",
        "csv_size_kb":  round(os.path.getsize(caminho_usado) / 1024, 1) if caminho_usado != "sqlite_db" else 0.0,
        "qc":           {},
        "alertas":      [],
        "n_obs":        int(len(df)),
        "n_atletas":    n_atl,
        "n_dias":       n_dias,
        "colunas":      list(df.columns),
    }
    return df, meta


def _ler_csv_seguro(caminho: str, colunas_fallback: list = None) -> pd.DataFrame:
    if not os.path.exists(caminho):
        return pd.DataFrame(columns=colunas_fallback) if colunas_fallback else pd.DataFrame()
    try:
        return pd.read_csv(caminho, encoding="utf-8-sig")
    except Exception:
        try:
            return pd.read_csv(caminho, encoding="latin-1")
        except Exception:
            return pd.DataFrame(columns=colunas_fallback) if colunas_fallback else pd.DataFrame()


def carregar_mapa_anonimizacao():
    p = os.path.join(OUT_DIR, "mapa_anonimizacao.csv")
    return _ler_csv_seguro(p, colunas_fallback=["nome_real", "codigo_anonimo"])


def carregar_ietj_por_fase():
    p = os.path.join(OUT_DIR, "ietj_por_fase.csv")
    return _ler_csv_seguro(p)


def carregar_ietj_faixas():
    p = os.path.join(OUT_DIR, "ietj_faixas.csv")
    return _ler_csv_seguro(p)


def carregar_posthoc():
    p = os.path.join(CACHE_DIR, "posthoc_wilcoxon.csv")
    return _ler_csv_seguro(p)


def carregar_rmcorr():
    p = os.path.join(CACHE_DIR, "rmcorr_resultados.csv")
    return _ler_csv_seguro(p)