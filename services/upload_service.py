import io
import pandas as pd
from repositories import get_db_connection, reset_db

def processar_csv_upload(contents: bytes) -> dict:
    # 1. Limpa a base de dados anterior para garantir análise isolada da sessão enviada
    reset_db()

    # 2. Ler CSV em memória
    df = pd.read_csv(io.BytesIO(contents))
    df.columns = [str(col).strip().lower() for col in df.columns]

    # Mapeamento Flexível de Colunas (Plataforma Crua VS Tratada)
    col_nome = next((c for c in ['player name', 'nome', 'player_name', 'atleta', 'player'] if c in df.columns), None)
    col_data = next((c for c in ['date', 'data', 'day'] if c in df.columns), None)
    col_md = next((c for c in ['microcycle_day', 'md', 'dia_microciclo', 'tags', 'session title', 'split name'] if c in df.columns), None)

    col_dist_km = next((c for c in ['distance (km)', 'distancia (km)', 'total distance (km)'] if c in df.columns), None)
    col_dist_m = next((c for c in ['distancia_m', 'distance_m', 'total_distance', 'distance (m)', 'total distance (m)'] if c in df.columns), None)

    col_dmin = next((c for c in ['distance per min (m/min)', 'distance_per_min', 'dist_per_min', 'm_min'] if c in df.columns), None)
    col_load = next((c for c in ['player load', 'player_load', 'load'] if c in df.columns), None)
    col_speed = next((c for c in ['top speed (km/h)', 'top_speed_kmh', 'max_speed', 'top_speed'] if c in df.columns), None)
    col_hsr = next((c for c in ['sprint distance (m)', 'hsr_m', 'hsr', 'high_speed_running'] if c in df.columns), None)
    col_acc = next((c for c in ['accelerations zone count: > 2 m/s/s', 'acc_count', 'accelerations', 'aceleracoes'] if c in df.columns), None)
    col_dec = next((c for c in ['deceleration zone count: > 2 m/s/s', 'dec_count', 'decelerations', 'desaceleracoes'] if c in df.columns), None)
    col_dur = next((c for c in ['duration', 'duration_min', 'duracao'] if c in df.columns), None)

    # Normalização de Distância (KM -> Metros se necessário)
    if col_dist_m:
        df['parsed_dist_m'] = df[col_dist_m].fillna(0.0)
    elif col_dist_km:
        df['parsed_dist_m'] = df[col_dist_km].fillna(0.0) * 1000.0
    else:
        df['parsed_dist_m'] = 0.0

    # Distância por Minuto (m/min)
    if col_dmin:
        df['parsed_dmin'] = df[col_dmin].fillna(0.0)
    else:
        df['parsed_dmin'] = df['parsed_dist_m'] / 90.0

    # Cálculo Automático de IETJ (%)
    if col_md and 'ietj' not in df.columns:
        md_series = df[col_md].astype(str).str.upper()
        md_rows = df[md_series.str.contains('MD', na=False)]
        ref_md = md_rows['parsed_dmin'].median() if not md_rows.empty else df['parsed_dmin'].median()
        df['ietj'] = (df['parsed_dmin'] / ref_md * 100.0) if ref_md and ref_md > 0 else 100.0
    elif 'ietj' not in df.columns:
        df['ietj'] = 100.0

    # Cálculo Automático de RSEI
    if col_load and 'rsei' not in df.columns:
        df['rsei'] = (df[col_load] / (df['parsed_dist_m'] + 1.0)) * 1000.0
    elif 'rsei' not in df.columns:
        df['rsei'] = 1.0

    conn = get_db_connection()
    cursor = conn.cursor()
    registos_inseridos = 0

    try:
        for _, row in df.iterrows():
            nome_atleta = str(row[col_nome]).strip() if col_nome and pd.notna(row[col_nome]) else "Atleta Desconhecido"
            data_sessao = str(row[col_data]).strip() if col_data and pd.notna(row[col_data]) else "2025-07-16"

            raw_md = str(row[col_md]).strip().upper() if col_md and pd.notna(row[col_md]) else "TREINO GPS"
            md_day = raw_md if "MD" in raw_md else "MD-3"

            dist = float(row['parsed_dist_m'])
            dmin = float(row['parsed_dmin'])
            load = float(row[col_load]) if col_load and pd.notna(row[col_load]) else 0.0
            speed = float(row[col_speed]) if col_speed and pd.notna(row[col_speed]) else 0.0
            hsr = float(row[col_hsr]) if col_hsr and pd.notna(row[col_hsr]) else 0.0
            acc = float(row[col_acc]) if col_acc and pd.notna(row[col_acc]) else 0.0
            dec = float(row[col_dec]) if col_dec and pd.notna(row[col_dec]) else 0.0
            dur = float(row[col_dur]) if col_dur and pd.notna(row[col_dur]) else 90.0
            if dur > 500:
                dur = dur / 60.0

            ietj_val = float(row['ietj']) if 'ietj' in row and pd.notna(row['ietj']) else 100.0
            rsei_val = float(row['rsei']) if 'rsei' in row and pd.notna(row['rsei']) else 1.0

            cursor.execute("INSERT OR IGNORE INTO jogadores (nome, posicao) VALUES (?, ?)", (nome_atleta, "Campo"))
            cursor.execute("SELECT id FROM jogadores WHERE nome = ?", (nome_atleta,))
            jogador_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM sessoes WHERE data = ?", (data_sessao,))
            row_sessao = cursor.fetchone()
            if row_sessao:
                sessao_id = row_sessao[0]
            else:
                cursor.execute("INSERT INTO sessoes (data, tipo) VALUES (?, ?)", (data_sessao, md_day))
                sessao_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO registos (
                    jogador_id, sessao_id, microcycle_day, duration_min, distancia_m,
                    distance_per_min, player_load, top_speed_kmh, hsr_m, acc_count,
                    dec_count, ietj, rsei
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (jogador_id, sessao_id, md_day, dur, dist, dmin, load, speed, hsr, acc, dec, ietj_val, rsei_val))
            registos_inseridos += 1

        conn.commit()
    finally:
        conn.close()

    return {"status": "sucesso", "novos_registos": registos_inseridos}