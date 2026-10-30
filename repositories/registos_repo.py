import sqlite3

def registo_existe(cursor, jogador_id, sessao_id):
    cursor.execute("SELECT id FROM registos WHERE jogador_id = ? AND sessao_id = ?", (jogador_id, sessao_id))
    return cursor.fetchone() is not None

def inserir_registo(cursor, dados):
    query = """
        INSERT INTO registos 
        (jogador_id, sessao_id, microcycle_day, duration_min, distancia_m, distance_per_min, 
         player_load, top_speed_kmh, hsr_m, acc_count, dec_count, ietj, rsei)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (
        dados.get("jogador_id"),
        dados.get("sessao_id"),
        dados.get("microcycle_day"),
        dados.get("duration_min"),
        dados.get("distancia_m"),
        dados.get("distance_per_min"),
        dados.get("player_load"),
        dados.get("top_speed_kmh"),
        dados.get("hsr_m"),
        dados.get("acc_count"),
        dados.get("dec_count"),
        dados.get("ietj"),
        dados.get("rsei")
    ))

def limpar_base_dados(conn):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registos")
    cursor.execute("DELETE FROM sessoes")
    cursor.execute("DELETE FROM jogadores")
    cursor.execute("DELETE FROM sqlite_sequence")
    conn.commit()

def obter_totais_dashboard(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM registos")
    res_reg = cursor.fetchone()
    total_registos = res_reg["total"] if res_reg else 0
    
    cursor.execute("SELECT COUNT(*) as total FROM jogadores")
    res_jog = cursor.fetchone()
    total_jogadores = res_jog["total"] if res_jog else 0
    
    cursor.execute("SELECT COUNT(*) as total FROM sessoes")
    res_ses = cursor.fetchone()
    total_sessoes = res_ses["total"] if res_ses else 0
    
    cursor.execute("SELECT AVG(ietj) as avg_ietj, AVG(rsei) as avg_rsei FROM registos")
    medias = cursor.fetchone()
    
    avg_ietj = round(medias["avg_ietj"], 1) if medias and medias["avg_ietj"] else 0.0
    avg_rsei = round(medias["avg_rsei"], 2) if medias and medias["avg_rsei"] else 0.0
    
    return {
        "total_registos": total_registos,
        "total_jogadores": total_jogadores,
        "total_sessoes": total_sessoes,
        "avg_ietj": avg_ietj,
        "avg_rsei": avg_rsei
    }

def obter_dados_graficos(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.nome,
               ROUND(SUM(r.player_load), 1) as total_load,
               ROUND(AVG(r.distancia_m), 1) as avg_dist,
               ROUND(AVG(r.ietj), 1) as avg_ietj,
               ROUND(AVG(r.rsei), 2) as avg_rsei
        FROM registos r
        JOIN jogadores j ON r.jogador_id = j.id
        GROUP BY j.id, j.nome
        ORDER BY j.id ASC
        LIMIT 15
    """)
    rows = cursor.fetchall()
    
    labels = [r["nome"] for r in rows]
    player_load = [r["total_load"] or 0 for r in rows]
    distancia = [r["avg_dist"] or 0 for r in rows]
    ietj = [r["avg_ietj"] or 0 for r in rows]
    rsei = [r["avg_rsei"] or 0 for r in rows]
    
    return {
        "labels": labels,
        "player_load": player_load,
        "distancia": distancia,
        "ietj": ietj,
        "rsei": rsei
    }
