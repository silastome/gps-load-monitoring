import numpy as np
import pandas as pd


def distribuicao_fases(df):
    if 'microcycle_day' not in df.columns or df['microcycle_day'].dropna().empty:
        return pd.DataFrame({'fase': ['MD'], 'n': [len(df)]})
    cont = df['microcycle_day'].astype(str).value_counts().reset_index()
    cont.columns = ['fase', 'n']
    return cont


def distribuicao_acwr(df):
    if 'acwr_zone' not in df.columns or df['acwr_zone'].dropna().empty:
        return pd.DataFrame({'zona': ['Sem histórico suficiente (< 7 dias)'], 'n': [len(df)], 'pct': [100.0]})
    
    cont = df['acwr_zone'].value_counts()
    total = int(cont.sum())
    if total == 0:
        return pd.DataFrame({'zona': ['Sem histórico suficiente (< 7 dias)'], 'n': [len(df)], 'pct': [100.0]})

    linhas = []
    for z, n in cont.items():
        linhas.append({'zona': str(z), 'n': int(n), 'pct': round(int(n) / total * 100, 1)})
    return pd.DataFrame(linhas)


def resumo_foster(df):
    if 'monotony_player_load' not in df.columns or df['monotony_player_load'].dropna().empty:
        return {"monotonia_media": None, "strain_medio": None}
    
    m = df["monotony_player_load"].dropna()
    s = df["strain_player_load"].dropna() if "strain_player_load" in df.columns else pd.Series(dtype=float)
    
    return {
        "monotonia_media": round(float(m.mean()), 2) if len(m) else None,
        "strain_medio": round(float(s.mean()), 2) if len(s) else None,
    }
