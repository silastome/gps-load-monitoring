import re
import numpy as np
import pandas as pd

MAPA_COLUNAS_POSSIVEIS = {
    'date': ['date', 'data', 'day', 'timestamp', 'datetime', 'sessaodata'],
    'player_name': ['playername', 'player', 'atleta', 'nome', 'athletename', 'athlete'],
    'duration': ['duration', 'durationsecs', 'duracaos', 'times', 'durations', 'durationmin', 'duracao'],
    'distance': ['distancekm', 'distancem', 'distance', 'distancia', 'totaldistance', 'distm', 'distanciam'],
    'player_load': ['playerload', 'pl', 'totalplayerload', 'carga'],
    'top_speed_kmh': ['topspeedkmh', 'topspeed', 'vmax', 'maxspeed'],
    'max_acceleration': ['maxaccelerationmss', 'maxacceleration', 'maxacc', 'aceleracaomax', 'accmax'],
    'max_deceleration': ['maxdecelerationmss', 'maxdeceleration', 'maxdec', 'desaceleracaomax', 'decmax'],
    'microcycle_day': ['microcycleday', 'fase', 'diamicrociclo', 'mdday', 'periodomd', 'sessiontitle'],
    'split_name': ['splitname', 'split', 'subperiodo']
}


def clean_col(name):
    return re.sub(r'[^a-zA-Z0-9]', '', str(name)).lower()


def parse_data_robusta(series):
    def parse_val(v):
        if pd.isna(v):
            return pd.NaT
        try:
            val_num = float(v)
            if 30000 < val_num < 60000:
                return pd.to_datetime(val_num, unit='D', origin='1899-12-30')
        except (ValueError, TypeError):
            pass
        return pd.to_datetime(v, errors='coerce')
    return series.apply(parse_val)


def anonimizar_atletas(series: pd.Series) -> pd.Series:
    nomes_unicos = sorted(series.dropna().astype(str).unique().tolist())
    mapa_anonimo = {nome: f"A{idx + 1:02d}" for idx, nome in enumerate(nomes_unicos)}
    return series.astype(str).map(mapa_anonimo)


def mapear_colunas(df: pd.DataFrame) -> pd.DataFrame:
    colunas_originais = {clean_col(c): c for c in df.columns}
    renomear = {}

    for col_padrao, variacoes in MAPA_COLUNAS_POSSIVEIS.items():
        for var in variacoes:
            clean_var = clean_col(var)
            if clean_var in colunas_originais:
                renomear[colunas_originais[clean_var]] = col_padrao
                break

    df = df.rename(columns=renomear)

    if 'split_name' in df.columns:
        df_all = df[df['split_name'].astype(str).str.lower().str.strip() == 'all']
        if not df_all.empty:
            df = df_all.copy()

    if 'date' in df.columns:
        df['date'] = parse_data_robusta(df['date'])
    else:
        df['date'] = pd.Timestamp.today()

    if 'player_name' in df.columns:
        df['player_name'] = anonimizar_atletas(df['player_name'])
    else:
        df['player_name'] = 'A01'

    if 'microcycle_day' not in df.columns:
        df['microcycle_day'] = 'MD'

    if 'distance' in df.columns:
        val_med = df['distance'].dropna().median() if not df['distance'].dropna().empty else 0
        if val_med < 50:
            df['distance_m'] = df['distance'] * 1000.0
        else:
            df['distance_m'] = df['distance']

    if 'duration' in df.columns:
        val_med = df['duration'].dropna().median() if not df['duration'].dropna().empty else 0
        if val_med > 300:
            df['duration_secs'] = df['duration']
            df['duration_min'] = df['duration'] / 60.0
        else:
            df['duration_min'] = df['duration']
            df['duration_secs'] = df['duration'] * 60.0

    return df


def calcular_metricas_completas(df: pd.DataFrame) -> pd.DataFrame:
    df = mapear_colunas(df)
    df = df.drop_duplicates(subset=['player_name', 'date']).sort_values(['date', 'player_name']).reset_index(drop=True)

    if 'distance_m' in df.columns and 'duration_min' in df.columns:
        df['distance_per_min'] = df['distance_m'] / df['duration_min'].replace(0, np.nan)

    if 'player_load' in df.columns and 'duration_min' in df.columns:
        df['pl_per_min'] = df['player_load'] / df['duration_min'].replace(0, np.nan)

    if 'max_deceleration' in df.columns:
        df['max_deceleration'] = df['max_deceleration'].abs()

    return df
