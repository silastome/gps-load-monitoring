import io
import pandas as pd
from repositories import get_db_connection
from repositories.jogadores_repo import obter_ou_criar_jogador
from repositories.sessoes_repo import obter_ou_criar_sessao
from repositories.registos_repo import registo_existe, inserir_registo

def processar_csv_upload(conteudo_bytes: bytes, db_path=None):
    df = pd.read_csv(io.BytesIO(conteudo_bytes))
    df.columns = df.columns.str.strip().str.lower()
    
    col_atleta = next((c for c in ["player_name", "nome", "atleta", "player"] if c in df.columns), None)
    if not col_atleta:
        raise ValueError("Ficheiro CSV inválido: coluna de identificação do atleta não encontrada.")
    
    col_data = next((c for c in ["date", "data", "sessao_data"] if c in df.columns), None)
    col_dist = next((c for c in ["distance_m", "distancia_m", "distancia"] if c in df.columns), None)
    col_pl = next((c for c in ["player_load", "pl", "carga"] if c in df.columns), None)
    col_vmax = next((c for c in ["top_speed_kmh", "top_speed", "vmax"] if c in df.columns), None)
    col_hsr = next((c for c in ["hsr_m", "hsr", "sprint_m"] if c in df.columns), None)
    col_dur = next((c for c in ["duration_min", "duracao", "duration"] if c in df.columns), None)
    col_mc = next((c for c in ["microcycle_day", "microciclo", "dia"] if c in df.columns), None)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    linhas_aceites = 0
    linhas_rejeitadas = 0
    novos_registos = 0
    erros = []

    try:
        for idx, row in df.iterrows():
            num_linha = idx + 2
            
            val_atleta = row.get(col_atleta)
            nome_real = str(val_atleta).strip() if pd.notnull(val_atleta) else ""
            if not nome_real or nome_real.lower() == "nan":
                linhas_rejeitadas += 1
                erros.append("Linha " + str(num_linha) + ": Nome de atleta ausente.")
                continue

            val_data = row.get(col_data) if col_data else None
            data_sessao = str(val_data).strip() if pd.notnull(val_data) else ""
            if not data_sessao or data_sessao.lower() == "nan":
                linhas_rejeitadas += 1
                erros.append("Linha " + str(num_linha) + ": Data de sessão ausente para '" + nome_real + "'.")
                continue

            def safe_float(val):
                if pd.notnull(val):
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
                return None

            distancia = safe_float(row.get(col_dist)) if col_dist else None
            player_load = safe_float(row.get(col_pl)) if col_pl else None
            top_speed = safe_float(row.get(col_vmax)) if col_vmax else None
            hsr = safe_float(row.get(col_hsr)) if col_hsr else None
            duracao = safe_float(row.get(col_dur)) if col_dur else None

            val_mc = row.get(col_mc) if col_mc else None
            microcycle = str(val_mc).strip() if pd.notnull(val_mc) else None

            if any(val is not None and val < 0 for val in [distancia, player_load, top_speed, hsr, duracao]):
                linhas_rejeitadas += 1
                erros.append("Linha " + str(num_linha) + ": Métricas físicas com valores negativos para '" + nome_real + "'.")
                continue

            jogador_id, _ = obter_ou_criar_jogador(cursor, nome_real)
            tipo_sessao = microcycle if microcycle else "Treino Principal"
            sessao_id = obter_ou_criar_sessao(cursor, data_sessao, tipo_sessao)

            if registo_existe(cursor, jogador_id, sessao_id):
                linhas_rejeitadas += 1
                erros.append("Linha " + str(num_linha) + ": Registo duplicado para '" + nome_real + "' na sessão '" + data_sessao + "'.")
                continue

            ietj = round((player_load / 300.0) * 100, 1) if player_load is not None and player_load > 0 else None
            rsei = round((top_speed * 1.5) + (hsr / 100.0), 2) if top_speed is not None and hsr is not None else None
            dist_per_min = round(distancia / duracao, 2) if distancia is not None and duracao is not None and duracao > 0 else None

            dados_registo = {
                "jogador_id": jogador_id,
                "sessao_id": sessao_id,
                "microcycle_day": microcycle,
                "duration_min": duracao,
                "distancia_m": distancia,
                "distance_per_min": dist_per_min,
                "player_load": player_load,
                "top_speed_kmh": top_speed,
                "hsr_m": hsr,
                "acc_count": None,
                "dec_count": None,
                "ietj": ietj,
                "rsei": rsei
            }

            inserir_registo(cursor, dados_registo)
            novos_registos += 1
            linhas_aceites += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return {
        "novos_registos": novos_registos,
        "linhas_aceites": linhas_aceites,
        "linhas_rejeitadas": linhas_rejeitadas,
        "erros": erros
    }
