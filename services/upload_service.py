import pandas as pd
import io
from repositories import get_connection

def processar_e_ingestao_csv(conteudo_bytes):
    df = pd.read_csv(io.BytesIO(conteudo_bytes))
    registos_inseridos = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        for _, row in df.iterrows():
            nome = str(row.get('player_name', row.get('nome', 'Atleta Desconhecido')))
            cursor.execute("INSERT OR IGNORE INTO jogadores (nome) VALUES (?)", (nome,))
            cursor.execute("SELECT id FROM jogadores WHERE nome = ?", (nome,))
            res = cursor.fetchone()
            jogador_id = res['id'] if res else None
            
            data_sessao = str(row.get('date', row.get('data', '2025-01-01')))
            cursor.execute("INSERT OR IGNORE INTO sessoes (data) VALUES (?)", (data_sessao,))
            cursor.execute("SELECT id FROM sessoes WHERE data = ?", (data_sessao,))
            res_s = cursor.fetchone()
            sessao_id = res_s['id'] if res_s else None
            
            dist = float(row.get('distance_m', 0.0))
            pl = float(row.get('player_load', 0.0))
            ts = float(row.get('top_speed_kmh', 0.0))
            
            cursor.execute("""
                INSERT INTO registos (jogador_id, sessao_id, distancia_m, player_load, top_speed_kmh)
                VALUES (?, ?, ?, ?, ?)
            """, (jogador_id, sessao_id, dist, pl, ts))
            registos_inseridos += 1
        conn.commit()
    return {"registos_processados": registos_inseridos}
