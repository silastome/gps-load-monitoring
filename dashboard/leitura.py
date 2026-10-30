import os
import json
import hashlib
import pandas as pd

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR   = os.path.join(BASE_DIR, "outputs")
CACHE_DIR = os.path.join(BASE_DIR, "cache")


def _sha256_curto(caminho, n_bytes=8):
    if not os.path.exists(caminho):
        return "n/a"
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        h.update(f.read(65536))
    return h.hexdigest()[:n_bytes]


def carregar_dashboard():
    csv_dash = os.path.join(OUT_DIR, "conversao_dash_final.csv")
    if not os.path.exists(csv_dash):
        raise FileNotFoundError("Nao encontrei %s" % csv_dash)

    df = pd.read_csv(csv_dash)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    qc_path = os.path.join(CACHE_DIR, "qc_report.json")
    if os.path.exists(qc_path):
        with open(qc_path) as f:
            qc = json.load(f)
    else:
        qc = {}

    alertas = []
    if qc:
        if len(df) != qc.get("registos_finais"):
            alertas.append("N obs (%d) difere do QC (%s)" % (len(df), qc.get("registos_finais")))
        if df["player_name"].nunique() != qc.get("atletas_incluidos"):
            alertas.append("N atletas (%d) difere do QC" % df["player_name"].nunique())
        if df["date"].dt.date.nunique() != qc.get("dias_monitorizados"):
            alertas.append("N dias (%d) difere do QC" % df["date"].dt.date.nunique())

    meta = {
        "csv_path":     csv_dash,
        "csv_sha":      _sha256_curto(csv_dash),
        "csv_size_kb":  round(os.path.getsize(csv_dash) / 1024, 1),
        "qc":           qc,
        "alertas":      alertas,
        "n_obs":        int(len(df)),
        "n_atletas":    int(df["player_name"].nunique()),
        "n_dias":       int(df["date"].dt.date.nunique()),
        "colunas":      list(df.columns),
    }
    return df, meta


def carregar_mapa_anonimizacao():
    p = os.path.join(OUT_DIR, "mapa_anonimizacao.csv")
    if not os.path.exists(p):
        return pd.DataFrame(columns=["nome_real", "codigo_anonimo"])
    return pd.read_csv(p)


def carregar_ietj_por_fase():
    p = os.path.join(OUT_DIR, "ietj_por_fase.csv")
    if not os.path.exists(p):
        return pd.DataFrame()
    return pd.read_csv(p)


def carregar_ietj_faixas():
    p = os.path.join(OUT_DIR, "ietj_faixas.csv")
    if not os.path.exists(p):
        return pd.DataFrame()
    return pd.read_csv(p)


def carregar_posthoc():
    p = os.path.join(CACHE_DIR, "posthoc_wilcoxon.csv")
    if not os.path.exists(p):
        return pd.DataFrame()
    return pd.read_csv(p)


def carregar_rmcorr():
    p = os.path.join(CACHE_DIR, "rmcorr_resultados.csv")
    if not os.path.exists(p):
        return pd.DataFrame()
    return pd.read_csv(p)
