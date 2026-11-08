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
from typing import Union
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
    'acc_count': [
        'acccount', 'accelerations', 'accelcount', 'totalaccelerations', 'nacc',
        'accelerationszonecount', 'accelscount', 'contagemaceleracoes', 'aceleracoes'
    ],
    'dec_count': [
        'deccount', 'decelerations', 'decelcount', 'totaldecelerations', 'ndec',
        'decelerationzonecount', 'decelscount', 'contagemdesaceleracoes', 'desaceleracoes'
    ],
    'hsr_m': [
        'hsrm', 'hsr', 'highspeedrunning', 'highspeedrunningdistance',
        'distanciaaltavelocidade', 'sprintdistancezone4', 'zone4distance', 'distancezone4m',
        'distanceinspeedzone4km', 'distanceinspeedzone4m'
    ],
    'sprint_m': [
        'sprintm', 'sprint', 'sprintdistance', 'sprintdistancem', 'distanciasprint',
        'sprintdistancezone5', 'zone5distance', 'distancezone5m',
        'distanceinspeedzone5km', 'distanceinspeedzone5m'
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
    """Normaliza o nome da coluna removendo caracteres especiais e espaços."""
    return re.sub(r'[^a-zA-Z0-9]', '', str(name)).lower()


def safe_numeric(series: pd.Series) -> pd.Series:
    """Converte com segurança valores numéricos (incluindo vírgula como decimal)."""
    if series.dtype in [np.float64, np.int64]:
        return series
    cleaned = series.astype(str).str.replace(',', '.', regex=False)
    cleaned = cleaned.str.extract(r'([-+]?\d*\.?\d+)')[0]
    return pd.to_numeric(cleaned, errors='coerce')


def parse_data_robusta(series: pd.Series) -> pd.Series:
    """Converte strings e números seriais de data (ex: Excel STATSports 45964) em Datetime."""
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
            res = pd.to_datetime(v, errors='coerce', dayfirst=False)
        return res

    return series.apply(parse_val)


def anonimizar_atletas(series: pd.Series, prefixo: str = "A") -> pd.Series:
    """Substitui nomes de atletas por códigos anonimizados ordenados (ex: A01, A02)."""
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
    """Mapeia e converte colunas de qualquer fornecedor de GPS para o esquema padronizado."""
    df_out = df.copy()
    colunas_originais = {clean_col(c): c for c in df_out.columns}

    # Agregação automática de contagem de acelerações/desacelerações RAW (ex: STATSports)
    acc_zone_cols = [c for c in df_out.columns if 'Accelerations Zone Count' in str(c)]
    dec_zone_cols = [c for c in df_out.columns if 'Deceleration Zone Count' in str(c)]

    if acc_zone_cols and 'acc_count' not in [clean_col(c) for c in df_out.columns]:
        df_out['acc_count'] = df_out[acc_zone_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)

    if dec_zone_cols and 'dec_count' not in [clean_col(c) for c in df_out.columns]:
        df_out['dec_count'] = df_out[dec_zone_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)

    renomear = {}
    for col_padrao, variacoes in MAPA_COLUNAS_POSSIVEIS.items():
        for var in variacoes:
            clean_var = clean_col(var)
            if clean_var in colunas_originais:
                renomear[colunas_originais[clean_var]] = col_padrao
                break

    df_out = df_out.rename(columns=renomear)

    # Filtrar apenas o bloco completo da sessão se o ficheiro contiver múltiplos splits
    if 'split_name' in df_out.columns:
        mask_all = df_out['split_name'].astype(str).str.lower().str.strip().isin(
            ['all', 'full', 'sessao_completa', 'total', 'session', 'training']
        )
        if mask_all.any():
            df_out = df_out[mask_all].copy()

    # Tratamento da data
    if 'date' in df_out.columns:
        df_out['date'] = parse_data_robusta(df_out['date'])
    else:
        df_out['date'] = pd.Timestamp.today().normalize()

    # Anonimização ou limpeza de nomes
    if 'player_name' in df_out.columns:
        if anonimizar:
            df_out['player_name'] = anonimizar_atletas(df_out['player_name'], prefixo=prefixo_anonimo)
        else:
            df_out['player_name'] = df_out['player_name'].astype(str).str.strip()
    else:
        df_out['player_name'] = f"{prefixo_anonimo}01"

    if 'position' not in df_out.columns:
        df_out['position'] = 'N/D'

    # Normalização da etiqueta de microciclo (ex: extract MD/MD+1 do título da sessão)
    if 'microcycle_day' not in df_out.columns:
        df_out['microcycle_day'] = 'MD'
    else:
        def clean_mc(v):
            if pd.isna(v):
                return 'MD'
            s = str(v).strip()
            mc_match = re.search(r'(MD[+-]?\d*)', s, re.IGNORECASE)
            if mc_match:
                return mc_match.group(1).upper()
            return s if s else 'MD'
        df_out['microcycle_day'] = df_out['microcycle_day'].apply(clean_mc)

    # Conversão de Distância (km -> m se a mediana for < 50)
    if 'distance' in df_out.columns:
        df_out['distance'] = safe_numeric(df_out['distance'])
        val_med = df_out['distance'].dropna().median() if not df_out['distance'].dropna().empty else 0
        if val_med < 50:
            df_out['distance_m'] = df_out['distance'] * 1000.0
        else:
            df_out['distance_m'] = df_out['distance']

    # Conversão de Duração (segundos vs minutos)
    if 'duration' in df_out.columns:
        df_out['duration'] = safe_numeric(df_out['duration'])
        val_med = df_out['duration'].dropna().median() if not df_out['duration'].dropna().empty else 0
        if val_med > 300:
            df_out['duration_secs'] = df_out['duration']
            df_out['duration_min'] = df_out['duration'] / 60.0
        else:
            df_out['duration_min'] = df_out['duration']
            df_out['duration_secs'] = df_out['duration'] * 60.0

    # Conversão de HSR e Sprint se reportados em km em ficheiros RAW
    if 'hsr_m' in df_out.columns:
        df_out['hsr_m'] = safe_numeric(df_out['hsr_m'])
        val_max_hsr = df_out['hsr_m'].dropna().max() if not df_out['hsr_m'].dropna().empty else 0
        if 0 < val_max_hsr < 50:
            df_out['hsr_m'] = df_out['hsr_m'] * 1000.0

    if 'sprint_m' in df_out.columns:
        df_out['sprint_m'] = safe_numeric(df_out['sprint_m'])
        val_max_sprint = df_out['sprint_m'].dropna().max() if not df_out['sprint_m'].dropna().empty else 0
        if 0 < val_max_sprint < 15:
            df_out['sprint_m'] = df_out['sprint_m'] * 1000.0

    for col_num in ['player_load', 'top_speed_kmh', 'max_acceleration', 'max_deceleration', 'acc_count', 'dec_count']:
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

    for _, df_atl in df.groupby('player_name'):
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
    """Calcula Monotonia e Strain (Foster, 1998) em grelha diária contínua."""
    if col_carga not in df.columns or 'date' not in df.columns or 'player_name' not in df.columns:
        return df

    dfs_atletas = []
    for _, df_atl in df.groupby('player_name'):
        df_atl = df_atl.copy().sort_values('date')
        
        datas_completas = pd.date_range(start=df_atl['date'].min(), end=df_atl['date'].max(), freq='D')
        df_daily = df_atl.groupby('date')[col_carga].sum().reindex(datas_completas, fill_value=0).reset_index()
        df_daily.columns = ['date', col_carga]

        mean_7d = df_daily[col_carga].rolling(window=7, min_periods=1).mean()
        std_7d = df_daily[col_carga].rolling(window=7, min_periods=1).std().fillna(1.0)
        
        df_daily['monotony'] = (mean_7d / std_7d.replace(0, 1.0)).round(2)
        
        df_merged = pd.merge(
            df_atl,
            df_daily[['date', 'monotony']],
            on='date',
            how='left'
        )
        df_merged['strain'] = (df_merged[col_carga] * df_merged['monotony']).round(2)
        dfs_atletas.append(df_merged)

    return pd.concat(dfs_atletas, ignore_index=True) if dfs_atletas else df


def calcular_metricas_completas(
    df: pd.DataFrame, 
    anonimizar: bool = True,
    prefixo_anonimo: str = "A"
) -> pd.DataFrame:
    """Função principal de processamento: mapeia, calcula métricas relativas, IETJ e RSEI."""
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

    # IETJ REAL (Baseado no MD real ou mediana de densidade)
    if 'player_load' in df.columns:
        df_md = df[df['microcycle_day'] == 'MD']
        ref_load = df_md['player_load'].median() if not df_md.empty and df_md['player_load'].median() > 0 else 300.0
        df['ietj'] = np.where(df['player_load'] > 0, ((df['player_load'] / ref_load) * 100).round(1), np.nan)

    # RSEI REAL (P95 Histórico Individual do Atleta)
    if 'top_speed_kmh' in df.columns:
        df.loc[df['top_speed_kmh'] > 38.5, 'top_speed_kmh'] = np.nan
        p95_atleta = df.groupby('player_name')['top_speed_kmh'].transform(lambda x: x.quantile(0.95)).fillna(30.0)
        df['rsei_individual'] = (df['top_speed_kmh'] / p95_atleta).round(3)
        df['rsei'] = df['rsei_individual']
        df['percent_vmax'] = (df['rsei_individual'] * 100.0).round(2)

    # EWMA e Foster (apenas se existirem múltiplas datas)
    if 'date' in df.columns and len(df['date'].dropna().unique()) > 1:
        col_carga_ref = 'player_load' if 'player_load' in df.columns else 'distance_m'
        if col_carga_ref in df.columns:
            df = calcular_acwr_ewma(df, col_carga=col_carga_ref)
            df = calcular_metricas_foster(df, col_carga=col_carga_ref)

    return df