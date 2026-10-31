"""
===============================================================================
MÓDULO DE LEITURA E CARREGAMENTO DE DADOS PARA O DASHBOARD
===============================================================================
Descrição: Garante o carregamento robusto e seguro do conjunto de dados
           principal e dos relatórios estatísticos (QC, IETJ, Post-hoc, rmcorr).
===============================================================================
"""

import os
import json
import hashlib
import pandas as pd

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR   = os.path.join(BASE_DIR, "outputs")
CACHE_DIR = os.path.join(BASE_DIR, "cache")


def _sha256_curto(caminho, n_bytes=8):
    """Gera um hash SHA-256 encurtado para verificação de integridade do ficheiro."""
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
    Carrega o DataFrame principal e os metadados associados.
    Procura em ordem:
    1. outputs/conversao_dash_final.csv
    2. dados_base.csv (na raiz do projeto)
    3. Base de Dados SQLite via repository (fallback)
    """
    csv_dash = os.path.join(OUT_DIR, "conversao_dash_final.csv")
    csv_base = os.path.join(BASE_DIR, "dados_base.csv")

    caminho_usado = None
    if os.path.exists(csv_dash):
        caminho_usado = csv_dash
    elif os.path.exists(csv_base):
        caminho_usado = csv_base

    if not caminho_usado:
        # Fallback: tentar carregar diretamente da base de dados SQLite
        try:
            from repositories import get_db_connection
            from repositories.registos_repo import obter_dados_graficos
            conn = get_db_connection(db_path)
            df_db = obter_dados_graficos(conn)
            conn.close()
            if df_db is not None and not df_db.empty:
                df = df_db.copy()
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                
                n_atl = int(df["player_name"].nunique()) if "player_name" in df.columns else 0
                n_dias = int(df["date"].dt.date.nunique()) if "date" in df.columns else 0

                meta = {
                    "csv_path": "sqlite_db",
                    "csv_sha": "db",
                    "csv_size_kb": 0.0,
                    "qc": {},
                    "alertas": ["Dados carregados diretamente da base de dados SQLite."],
                    "n_obs": int(len(df)),
                    "n_atletas": n_atl,
                    "n_dias": n_dias,
                    "colunas": list(df.columns),
                }
                return df, meta
        except Exception:
            pass

        raise FileNotFoundError("Não foi encontrado o ficheiro de dados conversao_dash_final.csv nem dados_base.csv.")

    # Leitura segura com tratamento de encodings
    try:
        df = pd.read_csv(caminho_usado, encoding="utf-8-sig")
    except Exception:
        df = pd.read_csv(caminho_usado, encoding="latin-1")

    # Normalização da coluna de data
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = pd.Timestamp.today().normalize()

    # Leitura de relatórios de controlo de qualidade (QC)
    qc_path = os.path.join(CACHE_DIR, "qc_report.json")
    qc = {}
    if os.path.exists(qc_path):
        try:
            with open(qc_path, "r", encoding="utf-8") as f:
                qc = json.load(f)
        except Exception:
            qc = {}

    alertas = []
    if qc:
        reg_qc = qc.get("registos_finais")
        if reg_qc is not None and len(df) != reg_qc:
            alertas.append(f"N obs ({len(df)}) difere do QC ({reg_qc})")

        atl_qc = qc.get("atletas_incluidos")
        n_atl = df["player_name"].nunique() if "player_name" in df.columns else 0
        if atl_qc is not None and n_atl != atl_qc:
            alertas.append(f"N atletas ({n_atl}) difere do QC ({atl_qc})")

        dias_qc = qc.get("dias_monitorizados")
        n_dias = df["date"].dt.date.nunique() if "date" in df.columns else 0
        if dias_qc is not None and n_dias != dias_qc:
            alertas.append(f"N dias ({n_dias}) difere do QC ({dias_qc})")

    n_atl = int(df["player_name"].nunique()) if "player_name" in df.columns else 0
    n_dias = int(df["date"].dt.date.nunique()) if "date" in df.columns else 0

    meta = {
        "csv_path":     caminho_usado,
        "csv_sha":      _sha256_curto(caminho_usado),
        "csv_size_kb":  round(os.path.getsize(caminho_usado) / 1024, 1),
        "qc":           qc,
        "alertas":      alertas,
        "n_obs":        int(len(df)),
        "n_atletas":    n_atl,
        "n_dias":       n_dias,
        "colunas":      list(df.columns),
    }
    return df, meta


def _ler_csv_seguro(caminho, colunas_fallback=None):
    """Função auxiliar para leitura tolerante a falhas de CSVs secundários."""
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
    """Carrega o mapeamento entre nome real do atleta e código anónimo."""
    p = os.path.join(OUT_DIR, "mapa_anonimizacao.csv")
    return _ler_csv_seguro(p, colunas_fallback=["nome_real", "codigo_anonimo"])


def carregar_ietj_por_fase():
    """Carrega as métricas de Índice de Exposição Treino-Jogo por fase do microciclo."""
    p = os.path.join(OUT_DIR, "ietj_por_fase.csv")
    return _ler_csv_seguro(p)


def carregar_ietj_faixas():
    """Carrega as faixas de distribuição do IETJ."""
    p = os.path.join(OUT_DIR, "ietj_faixas.csv")
    return _ler_csv_seguro(p)


def carregar_posthoc():
    """Carrega os resultados dos testes estatísticos Post-hoc de Wilcoxon."""
    p = os.path.join(CACHE_DIR, "posthoc_wilcoxon.csv")
    return _ler_csv_seguro(p)


def carregar_rmcorr():
    """Carrega os resultados de correlação intra-individual (rmcorr)."""
    p = os.path.join(CACHE_DIR, "rmcorr_resultados.csv")
    return _ler_csv_seguro(p)