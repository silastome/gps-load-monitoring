"""
===============================================================================
SERVIÇO DE UPLOAD E INGESTÃO UNIVERSAL DE DADOS GPS
===============================================================================
Descrição: Recebe ficheiros CSV de qualquer fornecedor de GPS, aplica o
           processamento universal (gps_processor), valida os dados,
           persiste na base de dados SQLite e sincroniza o CSV consolidado.
===============================================================================
"""

import io
import os
import pandas as pd
import numpy as np

from repositories import get_db_connection
from repositories.jogadores_repo import obter_ou_criar_jogador
from repositories.sessoes_repo import obter_ou_criar_sessao
from repositories.registos_repo import registo_existe, inserir_registo
from services.gps_processor import calcular_metricas_completas

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def safe_float(val):
    """Converte valores com segurança para float, retornando None se inválido."""
    if pd.notnull(val):
        try:
            v = float(val)
            return v if not np.isnan(v) else None
        except (ValueError, TypeError):
            return None
    return None


def processar_csv_upload(
    conteudo_bytes: bytes, 
    db_path: str = None, 
    anonimizar: bool = False
) -> dict:
    """
    Processa o ficheiro CSV em bytes enviado via formulário/API.
    
    Parameters:
        conteudo_bytes: Conteúdo binário do ficheiro CSV.
        db_path: Caminho para a base de dados SQLite (opcional).
        anonimizar: Se True, anonimiza os nomes dos atletas durante a ingestão.
        
    Returns:
        dict: Resumo com estatísticas do processamento (aceites, rejeitados, erros).
    """
    # 1. Leitura inicial do CSV bruto
    try:
        df_raw = pd.read_csv(io.BytesIO(conteudo_bytes))
    except Exception as e:
        raise ValueError(f"Não foi possível ler o ficheiro CSV enviado: {str(e)}")

    if df_raw.empty:
        raise ValueError("O ficheiro CSV enviado está vazio.")

    # 2. Processamento universal via gps_processor (Mapeamento + Limpeza + Métricas)
    try:
        df_proc = calcular_metricas_completas(df_raw, anonimizar=anonimizar)
    except Exception as e:
        raise ValueError(f"Erro ao processar a estrutura do CSV: {str(e)}")

    # Verificação de colunas obrigatórias resultantes do gps_processor
    if 'player_name' not in df_proc.columns or df_proc['player_name'].dropna().empty:
        raise ValueError("Ficheiro CSV inválido: coluna de identificação do atleta não encontrada.")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    linhas_aceites = 0
    linhas_rejeitadas = 0
    novos_registos = 0
    erros = []
    registos_sincronizacao = []

    try:
        for idx, row in df_proc.iterrows():
            num_linha = idx + 2  # Considera o cabeçalho na linha 1

            # Validar Atleta
            val_atleta = row.get("player_name")
            nome_real = str(val_atleta).strip() if pd.notnull(val_atleta) else ""
            if not nome_real or nome_real.lower() in ["nan", "none", "n/d", "a00"]:
                linhas_rejeitadas += 1
                erros.append(f"Linha {num_linha}: Nome de atleta ausente ou inválido.")
                continue

            # Validar Data da Sessão
            val_data = row.get("date")
            data_dt = pd.to_datetime(val_data, errors='coerce') if pd.notnull(val_data) else pd.NaT
            if pd.isna(data_dt):
                linhas_rejeitadas += 1
                erros.append(f"Linha {num_linha}: Data de sessão ausente ou inválida para '{nome_real}'.")
                continue
            
            data_sessao_str = data_dt.strftime("%Y-%m-%d")

            # Extração de Métricas Físicas e Relativas
            distancia = safe_float(row.get("distance_m"))
            duracao = safe_float(row.get("duration_min"))
            player_load = safe_float(row.get("player_load"))
            top_speed = safe_float(row.get("top_speed_kmh"))
            hsr = safe_float(row.get("hsr_m"))
            sprint = safe_float(row.get("sprint_m"))
            
            acc_max = safe_float(row.get("max_acceleration"))
            dec_max = safe_float(row.get("max_deceleration"))

            val_mc = row.get("microcycle_day")
            microcycle = str(val_mc).strip() if pd.notnull(val_mc) else "MD"

            # Verificação de Valores Negativos
            metricas_checagem = [m for m in [distancia, duracao, player_load, top_speed, hsr, sprint] if m is not None]
            if any(m < 0 for m in metricas_checagem):
                linhas_rejeitadas += 1
                erros.append(f"Linha {num_linha}: Métricas físicas com valores negativos para '{nome_real}'.")
                continue

            # Cálculos Derivados Automáticos (se não vierem já no CSV)
            dist_per_min = safe_float(row.get("distance_per_min"))
            if dist_per_min is None and distancia is not None and duracao is not None and duracao > 0:
                dist_per_min = round(distancia / duracao, 2)

            pl_per_min = safe_float(row.get("pl_per_min"))
            if pl_per_min is None and player_load is not None and duracao is not None and duracao > 0:
                pl_per_min = round(player_load / duracao, 2)

            ietj = safe_float(row.get("ietj"))
            if ietj is None and player_load is not None and player_load > 0:
                ietj = round((player_load / 300.0) * 100, 1)

            rsei = safe_float(row.get("rsei"))
            if rsei is None and top_speed is not None and hsr is not None:
                rsei = round((top_speed * 1.5) + (hsr / 100.0), 2)

            # Persistência Relacional em DB (Atleta -> Sessão -> Registo)
            jogador_id, _ = obter_ou_criar_jogador(cursor, nome_real)
            tipo_sessao = microcycle if microcycle else "Treino Principal"
            sessao_id = obter_ou_criar_sessao(cursor, data_sessao_str, tipo_sessao)

            if registo_existe(cursor, jogador_id, sessao_id):
                linhas_rejeitadas += 1
                erros.append(f"Linha {num_linha}: Registo duplicado para '{nome_real}' na sessão '{data_sessao_str}'.")
                continue

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
                "acc_count": safe_float(row.get("acc_count")),
                "dec_count": safe_float(row.get("dec_count")),
                "ietj": ietj,
                "rsei": rsei
            }

            inserir_registo(cursor, dados_registo)
            novos_registos += 1
            linhas_aceites += 1
            registos_sincronizacao.append(row)

        conn.commit()

        # 3. Sincronização opcional do CSV unificado em outputs/conversao_dash_final.csv
        if registos_sincronizacao:
            os.makedirs(OUT_DIR, exist_ok=True)
            csv_final_path = os.path.join(OUT_DIR, "conversao_dash_final.csv")
            df_novos = pd.DataFrame(registos_sincronizacao)

            if os.path.exists(csv_final_path):
                try:
                    df_existente = pd.read_csv(csv_final_path)
                    df_concat = pd.concat([df_existente, df_novos], ignore_index=True)
                    df_concat = df_concat.drop_duplicates(subset=['player_name', 'date']).sort_values(['date', 'player_name'])
                    df_concat.to_csv(csv_final_path, index=False)
                except Exception:
                    df_novos.to_csv(csv_final_path, index=False)
            else:
                df_novos.to_csv(csv_final_path, index=False)

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