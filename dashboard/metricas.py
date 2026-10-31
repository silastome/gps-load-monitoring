"""
===============================================================================
MÓDULO DE MÉTRICAS, INSIGHTS AUTOMÁTICOS E ALERTAS CLÍNICOS
===============================================================================
Descrição: Funções para agregação de fases do microciclo, distribuição de 
           zonas de ACWR, resumo de Monotonia e Strain (Foster, 1998),
           geração de insights em linguagem natural e ficha individual do atleta.
===============================================================================
"""

import numpy as np
import pandas as pd


def distribuicao_fases(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a frequência absoluta de observações por dia do microciclo (ex: MD-4, MD-1)."""
    if 'microcycle_day' not in df.columns or df['microcycle_day'].dropna().empty:
        return pd.DataFrame({'fase': ['MD'], 'n': [len(df)]})
    
    s = df['microcycle_day'].dropna().astype(str).str.strip()
    s = s[~s.isin(['nan', 'None', 'N/D', ''])]
    
    if s.empty:
        return pd.DataFrame({'fase': ['MD'], 'n': [len(df)]})

    cont = s.value_counts().reset_index()
    cont.columns = ['fase', 'n']
    return cont


def distribuicao_acwr(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a distribuição percentual das zonas de risco do ACWR."""
    df_temp = df.copy()

    if 'acwr_zone' not in df_temp.columns or df_temp['acwr_zone'].dropna().empty:
        col_acwr = next(
            (c for c in ['acwr', 'acwr_ewma', 'acwr_ra'] if c in df_temp.columns and not df_temp[c].dropna().empty),
            None
        )
        if col_acwr:
            def categorizar_acwr(v):
                if pd.isna(v) or v is None:
                    return None
                if v < 0.80:
                    return 'Sub-treino (< 0.80)'
                elif 0.80 <= v <= 1.30:
                    return 'Sweet Spot (0.80 - 1.30)'
                elif 1.30 < v <= 1.50:
                    return 'Carga Elevada (1.30 - 1.50)'
                else:
                    return 'Risco Elevado (> 1.50)'
            
            df_temp['acwr_zone'] = pd.to_numeric(df_temp[col_acwr], errors='coerce').apply(categorizar_acwr)

    if 'acwr_zone' not in df_temp.columns or df_temp['acwr_zone'].dropna().empty:
        return pd.DataFrame({'zona': ['Sem histórico suficiente (< 7 dias)'], 'n': [len(df)], 'pct': [100.0]})

    cont = df_temp['acwr_zone'].dropna().value_counts()
    total = int(cont.sum())
    
    if total == 0:
        return pd.DataFrame({'zona': ['Sem histórico suficiente (< 7 dias)'], 'n': [len(df)], 'pct': [100.0]})

    linhas = []
    for z, n in cont.items():
        linhas.append({
            'zona': str(z), 
            'n': int(n), 
            'pct': round(int(n) / total * 100, 1)
        })
    return pd.DataFrame(linhas)


def resumo_foster(df: pd.DataFrame) -> dict:
    """Calcula os valores médios de Monotonia e Strain (Foster, 1998) da equipa."""
    col_m = next(
        (c for c in ['monotony_player_load', 'monotony', 'monotonia'] if c in df.columns and not df[c].dropna().empty),
        None
    )
    col_s = next(
        (c for c in ['strain_player_load', 'strain', 'strain_foster'] if c in df.columns and not df[c].dropna().empty),
        None
    )

    if not col_m:
        return {"monotonia_media": None, "strain_medio": None}

    m = pd.to_numeric(df[col_m], errors='coerce').dropna()
    s = pd.to_numeric(df[col_s], errors='coerce').dropna() if col_s else pd.Series(dtype=float)

    return {
        "monotonia_media": round(float(m.mean()), 2) if len(m) > 0 else None,
        "strain_medio": round(float(s.mean()), 2) if len(s) > 0 else None,
    }


def gerar_insights_sessao(df: pd.DataFrame) -> list:
    """Gera observações metodológicas em texto dinâmico para os cards do dashboard."""
    insights = []
    if df.empty:
        return insights

    # Intensidade
    if 'distance_per_min' in df.columns and not df['distance_per_min'].dropna().empty:
        int_media = df['distance_per_min'].mean()
        top_idx = df['distance_per_min'].idxmax()
        top_atleta = df.loc[top_idx, 'player_name'] if 'player_name' in df.columns else 'Destaque'
        top_val = df.loc[top_idx, 'distance_per_min']
        insights.append(
            f"⚡ <b>Intensidade Média da Equipa:</b> {int_media:.1f} m/min. "
            f"Maior pico registado pelo <b>{top_atleta}</b> ({top_val:.1f} m/min)."
        )

    # ACWR
    col_acwr = next((c for c in ['acwr_ewma', 'acwr_ra', 'acwr'] if c in df.columns), None)
    if col_acwr and not df[col_acwr].dropna().empty:
        risco = df[df[col_acwr] > 1.50]
        if not risco.empty and 'player_name' in df.columns:
            nomes = ", ".join(risco['player_name'].unique().tolist())
            insights.append(
                f"🚨 <b>Alerta de Sobrecarga (ACWR > 1.50):</b> {len(risco)} atleta(s) em risco: <b>{nomes}</b>."
            )
        else:
            insights.append("✅ <b>Carga Equilibrada:</b> Nenhum atleta em zona de pico crítico de ACWR.")

    # Monotonia
    col_m = next((c for c in ['monotony', 'monotony_player_load'] if c in df.columns), None)
    if col_m and not df[col_m].dropna().empty:
        alta = df[df[col_m] > 2.0]
        if not alta.empty:
            insights.append(f"⚠️ <b>Monotonia Elevada (> 2.0):</b> {len(alta)} atleta(s) com baixa variação nos últimos 7 dias.")

    return insights


def extrair_ficha_atleta(df: pd.DataFrame, player_name: str) -> dict:
    """Extrai os indicadores individuais e calcula Z-Score do atleta em relação ao grupo."""
    if 'player_name' not in df.columns:
        return {}
        
    r = df[df['player_name'] == player_name]
    if r.empty:
        return {}

    atleta_df = r.iloc[0]
    
    dist_val = float(atleta_df.get('distance_m', 0)) if pd.notnull(atleta_df.get('distance_m')) else 0.0
    dist_media = df['distance_m'].mean() if 'distance_m' in df.columns and not df['distance_m'].dropna().empty else 0.0
    dist_std = df['distance_m'].std() if 'distance_m' in df.columns and not df['distance_m'].dropna().empty else 1.0
    
    z_dist = (dist_val - dist_media) / (dist_std if dist_std > 0 else 1.0)

    return {
        "player_name": player_name,
        "distance_m": round(dist_val, 0),
        "player_load": round(float(atleta_df.get('player_load', 0)), 1) if pd.notnull(atleta_df.get('player_load')) else 0.0,
        "top_speed_kmh": round(float(atleta_df.get('top_speed_kmh', 0)), 1) if pd.notnull(atleta_df.get('top_speed_kmh')) else 0.0,
        "distance_per_min": round(float(atleta_df.get('distance_per_min', 0)), 1) if pd.notnull(atleta_df.get('distance_per_min')) else 0.0,
        "z_score_distancia": round(float(z_dist), 2),
        "status_mbi": "Acima do Padrão" if z_dist > 0.5 else ("Abaixo do Padrão" if z_dist < -0.5 else "Dentro do Padrão")
    }