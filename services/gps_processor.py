"""
===============================================================================
MÓDULO DE PROCESSAMENTO E NORMALIZAÇÃO DE DADOS GPS
===============================================================================
Descrição: Processador universal, agnóstico e multi-fornecedor (STATSports,
           Catapult One, GPExe, Oliver, Wimu, FieldWiz). Realiza limpeza,
           mapeamento de colunas, conversão de unidades, cálculo de métricas
           relativas (m/min, PL/min) e longitudinais (ACWR EWMA, Foster).
===============================================================================
"""

import re
import warnings
from typing import Optional, Union
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore', category=UserWarning, module='pandas')

MAPA_COLUNAS_POSSIVEIS = {
    'date': [
        'date', 'data', 'day', 'timestamp', 'datetime', 'sessaodata',
        'sessiondate', 'splitstartdate', 'perioddate', 'periodstartdate', 'dateiso'
    ],
    'player_name': [
        'playername', 'player', 'atleta', 'nome', 'athletename', 'athlete',
        'player_name', 'fullname', 'name', 'atletanome'
    ],
    'position': [
        'posicao', 'position', 'pos', 'role', 'grupo', 'group',
        'playerposition', 'tacticalposition'
    ],
    'duration': [
        'duration', 'durationsecs', 'duracaos', 'times', 'durations',
        'durationmin', 'duracao', 'totaltime', 'elapsedtime', 'periodduration'
    ],
    'distance': [
        'distancekm', 'distancem', 'distance', 'distancia', 'totaldistance',
        'distm', 'distanciam', 'totaldistancem', 'totaldistancekm'
    ],
    'player_load': [
        'playerload', 'pl', 'totalplayerload', 'carga', 'load',
        'impulseload', 'bodyload'
    ],
    'top_speed_kmh': [
        'topspeedkmh', 'topspeed', 'vmax', 'maxspeed', 'top_speed_kmh',
        'velocidademaxima', 'maxspeedkmh', 'maximumvelocitykmh', 'maxvelocitykmh', 'maxspeedm'
    ],
    'max_acceleration': [
        'maxaccelerationmss', 'maxacceleration', 'maxacc', 'aceleracaomax',
        'accmax', 'max_acceleration', 'peakacceleration', 'maximumaccelerationmss'
    ],
    'max_deceleration': [
        'maxdecelerationmss', 'maxdeceleration', 'maxdec', 'desaceleracaomax',
        'decmax', 'max_deceleration', 'peakdeceleration', 'maximumdecelerationmss'
    ],
    'hsr_m': [
        'hsrm', 'hsr', 'highspeedrunning', 'highspeedrunningdistance',
        'distanciaaltavelocidade', 'sprintdistancezone4', 'zone4distance', 'distancezone4m'
    ],
    'sprint_m': [
        'sprintm', 'sprint', 'sprintdistance', 'distanciasprint',
        'sprintdistancezone5', 'zone5distance', 'distancezone5m'
    ],
    'microcycle_day': [
        'microcycleday', 'fase', 'diamicrociclo', 'mdday', 'periodomd',
        'sessiontitle', 'microcycle', 'daytype', 'daysfrommatch'
    ],
    'split_name': [
        'splitname', 'split', 'subperiodo', 'periodname', 'tag', 'tags'
    ]
}


def clean_col(name: Union[str, int]) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', str(name)).lower()


def safe_numeric(series: pd.Series) -> pd.Series:
    if series.dtype in [np.float64, np.int64]:
        return series
    cleaned = series.astype(str).str.replace(',', '.', regex=False)
    cleaned = cleaned.str.extract(r'([-+]?\d*\.?\d+)')[0]
    return pd.to_numeric(cleaned, errors='coerce')


def parse_data_robusta(series: pd.Series) -> pd.Series:
    def parse_val(v):
        if pd.isna(v) or str(v).strip() == "":
            return pd.NaT
        try:
            val_num = float(v)
            if 30000 < val_num < 60000:
                return pd.to_datetime(val_num, unit='D', origin='1899-12-30')
        except (ValueError, TypeError):
            pass
        
        res = pd.to_datetime(v, errors='coerce', dayfirst=True)
        if pd.isna(res):
            res = pd.to_datetime(v, errors='coerce')
        return res

    return series.apply(parse_val)


def anonimizar_atletas(series: pd.Series, prefixo: str = "A") -> pd.Series:
    nomes_unicos = sorted(series.dropna().astype(str).unique().tolist())
    mapa_anonimo = {}
    
    idx_codigo = 1
    for nome in nomes_unicos:
        nome_clean = nome.strip()
        if re.match(r'^A\d+$', nome_clean, re.IGNORECASE):
            mapa_anonimo[nome] = nome_clean.upper()
        else:
            mapa_anonimo[nome] = f"{prefixo}{idx_codigo:02d}"
            idx_codigo += 1

    return series.astype(str).map(mapa_anonimo)


def mapear_colunas(
    df: pd.DataFrame, 
    anonimizar: bool = True,
    prefixo_anonimo: str = "A"
) -> pd.DataFrame:
    df_out = df.copy()
    colunas_originais = {clean_col(c): c for c in df_out.columns}
    renomear = {}

    for col_padrao, variacoes in MAPA_COLUNAS_POSSIVEIS.items():
        for var in variacoes:
            clean_var = clean_col(var)
            if clean_var in colunas_originais:
                renomear[colunas_originais[clean_var]] = col_padrao
                break

    df_out = df_out.rename(columns=renomear)

    if 'split_name' in df_out.columns:
        mask_all = df_out['split_name'].astype(str).str.lower().str.strip().isin(['all', 'full', 'sessao_completa', 'total', 'session'])
        if mask_all.any():
            df_out = df_out[mask_all].copy()

    if 'date' in df_out.columns:
        df_out['date'] = parse_data_robusta(df_out['date'])
    else:
        df_out['date'] = pd.Timestamp.today().normalize()

    if 'player_name' in df_out.columns:
        if anonimizar:
            df_out['player_name'] = anonimizar_atletas(df_out['player_name'], prefixo=prefixo_anonimo)
        else:
            df_out['player_name'] = df_out['player_name'].astype(str).str.strip()
    else:
        df_out['player_name'] = f"{prefixo_anonimo}01"

    if 'position' not in df_out.columns:
        df_out['position'] = 'N/D'

    if 'microcycle_day' not in df_out.columns:
        df_out['microcycle_day'] = 'MD'

    if 'distance' in df_out.columns:
        df_out['distance'] = safe_numeric(df_out['distance'])
        val_med = df_out['distance'].dropna().median() if not df_out['distance'].dropna().empty else 0
        if val_med < 50:
            df_out['distance_m'] = df_out['distance'] * 1000.0
        else:
            df_out['distance_m'] = df_out['distance']

    if 'duration' in df_out.columns:
        df_out['duration'] = safe_numeric(df_out['duration'])
        val_med = df_out['duration'].dropna().median() if not df_out['duration'].dropna().empty else 0
        if val_med > 300:
            df_out['duration_secs'] = df_out['duration']
            df_out['duration_min'] = df_out['duration'] / 60.0
        else:
            df_out['duration_min'] = df_out['duration']
            df_out['duration_secs'] = df_out['duration'] * 60.0

    for col_num in ['player_load', 'top_speed_kmh', 'max_acceleration', 'max_deceleration', 'hsr_m', 'sprint_m']:
        if col_num in df_out.columns:
            df_out[col_num] = safe_numeric(df_out[col_num])

    return df_out


def calcular_acwr_ewma(
    df: pd.DataFrame, 
    col_carga: str = 'player_load',
    dias_agudo: int = 7, 
    dias_cronico: int = 28
) -> pd.DataFrame:
    """Calcula ACWR EWMA contínuo (Williams et al., 2017) preenchendo off-days."""
    if col_carga not in df.columns or 'date' not in df.columns or 'player_name' not in df.columns:
        return df

    df = df.sort_values(['player_name', 'date']).reset_index(drop=True)
    dfs_atletas = []

    for atleta, df_atl in df.groupby('player_name'):
        df_atl = df_atl.copy()
        
        datas_completas = pd.date_range(start=df_atl['date'].min(), end=df_atl['date'].max(), freq='D')
        df_daily = df_atl.groupby('date')[col_carga].sum().reindex(datas_completas, fill_value=0).reset_index()
        df_daily.columns = ['date', col_carga]

        lambda_agudo = 2.0 / (dias_agudo + 1.0)
        lambda_cronico = 2.0 / (dias_cronico + 1.0)
        
        df_daily['acute_ewma'] = df_daily[col_carga].ewm(alpha=lambda_agudo, adjust=False).mean()
        df_daily['chronic_ewma'] = df_daily[col_carga].ewm(alpha=lambda_cronico, adjust=False).mean()
        df_daily['acwr_ewma'] = df_daily['acute_ewma'] / df_daily['chronic_ewma'].replace(0, np.nan)

        df_merged = pd.merge(
            df_atl, 
            df_daily[['date', 'acute_ewma', 'chronic_ewma', 'acwr_ewma']], 
            on='date', 
            how='left'
        )
        dfs_atletas.append(df_merged)

    if dfs_atletas:
        return pd.concat(dfs_atletas, ignore_index=True)
    return df


def calcular_metricas_foster(df: pd.DataFrame, col_carga: str = 'player_load') -> pd.DataFrame:
    """Calcula Monotonia e Strain (Foster, 1998)."""
    if col_carga not in df.columns or 'date' not in df.columns:
        return df

    dfs_atletas = []
    for atleta, df_atl in df.groupby('player_name'):
        df_atl = df_atl.copy().sort_values('date')
        
        mean_7d = df_atl[col_carga].rolling(window=7, min_periods=1).mean()
        std_7d = df_atl[col_carga].rolling(window=7, min_periods=1).std().fillna(1.0)
        
        df_atl['monotony'] = (mean_7d / std_7d.replace(0, 1.0)).round(2)
        df_atl['strain'] = (df_atl[col_carga] * df_atl['monotony']).round(2)
        
        dfs_atletas.append(df_atl)

    return pd.concat(dfs_atletas, ignore_index=True) if dfs_atletas else df


def calcular_metricas_completas(
    df: pd.DataFrame, 
    anonimizar: bool = True,
    prefixo_anonimo: str = "A"
) -> pd.DataFrame:
    """Função principal com RSEI individual por P95 e IETJ por MD real."""
    df = mapear_colunas(df, anonimizar=anonimizar, prefixo_anonimo=prefixo_anonimo)
    
    if 'player_name' in df.columns and 'date' in df.columns:
        df = df.drop_duplicates(subset=['player_name', 'date']).sort_values(['date', 'player_name']).reset_index(drop=True)

    if 'distance_m' in df.columns and 'duration_min' in df.columns:
        df['distance_per_min'] = np.where(df['duration_min'] > 0, (df['distance_m'] / df['duration_min']).round(2), 0.0)

    if 'player_load' in df.columns and 'duration_min' in df.columns:
        df['pl_per_min'] = np.where(df['duration_min'] > 0, (df['player_load'] / df['duration_min']).round(2), 0.0)

    if 'hsr_m' in df.columns and 'duration_min' in df.columns:
        df['hsr_per_min'] = np.where(df['duration_min'] > 0, (df['hsr_m'] / df['duration_min']).round(2), 0.0)

    if 'sprint_m' in df.columns and 'duration_min' in df.columns:
        df['sprint_per_min'] = np.where(df['duration_min'] > 0, (df['sprint_m'] / df['duration_min']).round(2), 0.0)

    if 'max_deceleration' in df.columns:
        df['max_deceleration'] = df['max_deceleration'].abs()

    # --- IETJ REAL (Baseado no MD real ou mediana de densidade) ---
    if 'player_load' in df.columns:
        df_md = df[df['microcycle_day'] == 'MD']
        ref_load = df_md['player_load'].median() if not df_md.empty and df_md['player_load'].median() > 0 else 300.0
        df['ietj'] = np.where(df['player_load'] > 0, ((df['player_load'] / ref_load) * 100).round(1), np.nan)

    # --- RSEI REAL (P95 Histórico Individual do Atleta) ---
    if 'top_speed_kmh' in df.columns:
        df.loc[df['top_speed_kmh'] > 38.5, 'top_speed_kmh'] = np.nan
        p95_atleta = df.groupby('player_name')['top_speed_kmh'].transform(lambda x: x.quantile(0.95)).fillna(30.0)
        df['rsei_individual'] = (df['top_speed_kmh'] / p95_atleta).round(3)
        df['rsei'] = df['rsei_individual']
        df['percent_vmax'] = (df['rsei_individual'] * 100.0).round(2)

    # --- EWMA e Foster ---
    if 'date' in df.columns and len(df['date'].dropna().unique()) > 1:
        col_carga_ref = 'player_load' if 'player_load' in df.columns else 'distance_m'
        if col_carga_ref in df.columns:
            df = calcular_acwr_ewma(df, col_carga=col_carga_ref)
            df = calcular_metricas_foster(df, col_carga=col_carga_ref)

    return df