import io
import pandas as pd
from repositories import get_db_connection

def processar_csv_upload(conteudo_bytes: bytes, db_path=None):
    """
    Processa o ficheiro CSV de GPS em memória, aplica anonimização automática,
    rejeita registos incompletos sem atleta e persiste na base de dados SQLite.
    """
    # 1. Leitura do CSV em memória
    df = pd.read_csv(io.BytesIO(conteudo_bytes))
    
    # Normalizar nomes das colunas
    df.columns = df.columns.str.strip().str.lower()
    
    # Mapeamento de colunas possíveis
    col_atleta = next((c for c in ['player_name', 'nome', 'atleta', 'player'] if c in df.columns), None)
    col_data = next((c for c in ['date', 'data', 'sessao_data'] if c in df.columns), 'date')
    col_dist = next((c for c in ['distance_m', 'distancia_m', 'distancia'] if c in df.columns), 'distance_m')
    col_pl = next((c for c in ['player_load', 'pl', 'carga'] if c in df.columns), 'player_load')
    col_vmax = next((c for c in ['top_speed_kmh', 'top_speed', 'vmax'] if c in df.columns), 'top_speed_kmh')
    col_hsr = next((c for c in ['hsr_m', 'hsr', 'sprint_m'] if c in df.columns), 'hsr_m')
    
    # Validação estrita: Rejeita o ficheiro se a coluna de identificação do atleta não existir
    if not col_atleta:
        raise ValueError("Ficheiro CSV inválido: coluna de identificação do atleta não encontrada.")
        
    # Rejeição estrita de registos incompletos: Elimina linhas onde o nome do atleta esteja ausente ou em branco
    df = df.dropna(subset=[col_atleta])
    df[col_atleta] = df[col_atleta].astype(str).str.strip()
    df = df[df[col_atleta] != ""]
    
    if df.empty:
        raise ValueError("Ficheiro CSV sem registos válidos de atletas.")

    # 2. Lógica de Anonimização Automática (Atleta 01, Atleta 02...)
    atletas_unicos = sorted(df[col_atleta].unique())
    mapa_anonimizado = {nome_real: f"Atleta {i+1:02d}" for i, nome_real in enumerate(atletas_unicos)}
    
    # 3. Persistência na Base de Dados Relacional
    conn = get_db_connection()
    cursor = conn.cursor()
    registos_processados = 0
    
    try:
        for idx, row in df.iterrows():
            nome_anonimo = mapa_anonimizado[row[col_atleta]]
            data_sessao = str(row.get(col_data, '2026-10-20')).strip()
            if data_sessao == 'nan' or not data_sessao:
                data_sessao = '2026-10-20'
            
            # Obter ou registar Jogador
            cursor.execute("SELECT id FROM jogadores WHERE nome = ?", (nome_anonimo,))
            res_j = cursor.fetchone()
            if res_j:
                jogador_id = res_j['id']
            else:
                cursor.execute("INSERT INTO jogadores (nome) VALUES (?)", (nome_anonimo,))
                jogador_id = cursor.lastrowid
            
            # Obter ou registar Sessão
            cursor.execute("SELECT id FROM sessoes WHERE data = ?", (data_sessao,))
            res_s = cursor.fetchone()
            if res_s:
                sessao_id = res_s['id']
            else:
                cursor.execute("INSERT INTO sessoes (data, tipo) VALUES (?, ?)", (data_sessao, "Treino Principal"))
                sessao_id = cursor.lastrowid
            
            # Extração de métricas físicas com conversão segura
            distancia = float(row.get(col_dist, 0.0)) if pd.notnull(row.get(col_dist)) else 0.0
            player_load = float(row.get(col_pl, 0.0)) if pd.notnull(row.get(col_pl)) else 0.0
            top_speed = float(row.get(col_vmax, 0.0)) if pd.notnull(row.get(col_vmax)) else 0.0
            hsr = float(row.get(col_hsr, 0.0)) if pd.notnull(row.get(col_hsr)) else 0.0
            
            ietj = round((player_load / 300.0) * 100, 1) if player_load > 0 else 75.0
            rsei = round((top_speed * 1.5) + (hsr / 100.0), 2)
            
            cursor.execute("""
                INSERT INTO registos 
                (jogador_id, sessao_id, distancia_m, player_load, top_speed_kmh, hsr_m, ietj, rsei)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (jogador_id, sessao_id, distancia, player_load, top_speed, hsr, ietj, rsei))
            
            registos_processados += 1
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    return registos_processados
