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
import sqlite3
import pandas as pd
import numpy as np

from repositories import get_db_connection
from repositories.jogadores_repo import obter_ou_criar_jogador
from repositories.sessoes_repo import obter_ou_criar_sessao
from repositories.registos_repo import registo_existe, inserir_registo
from services.gps_processor import calcular_metricas_completas

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")


def garantir_tabelas_db(conn: sqlite3.Connection):
    """Garante a existência de todas as tabelas e colunas na base de dados antes da gravação."""
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS jogadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE,
            nome_real TEXT UNIQUE,
            codigo_anonimo TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            data_sessao TEXT,
            tipo TEXT,
            tipo_sessao TEXT,
            UNIQUE(data, tipo)
        );
        CREATE TABLE IF NOT EXISTS registos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER NOT NULL,
            sessao_id INTEGER NOT NULL,
            date TEXT,
            player_name TEXT,
            duration_secs REAL,
            distance_m REAL,
            distancia_m REAL,
            player_load REAL,
            top_speed_kmh REAL,
            max_acceleration REAL,
            max_deceleration REAL,
            duration_min REAL,
            duracao_min REAL,
            distance_per_min REAL,
            distancia_per_min REAL,
            pl_per_min REAL,
            microcycle_day TEXT,
            week_id TEXT,
            iso_tuple TEXT,
            ano_iso INTEGER,
            semana_iso INTEGER,
            acute REAL,
            chronic REAL,
            acwr REAL,
            acwr_zone TEXT,
            percent_vmax REAL,
            carga_total_semanal REAL,
            monotony_player_load REAL,
            strain_player_load REAL,
            hsr_m REAL,
            sprint_m REAL,
            hsr_per_min REAL,
            sprint_per_min REAL,
            acc_count REAL,
            dec_count REAL,
            vmax_individual_p95 REAL,
            rsei_individual REAL,
            rsei REAL,
            cluster INTEGER,
            perfil_carga TEXT,
            periodo TEXT,
            ietj REAL,
            FOREIGN KEY (jogador_id) REFERENCES jogadores(id),
            FOREIGN KEY (sessao_id) REFERENCES sessoes(id),
            UNIQUE(jogador_id, sessao_id)
        );
    """)
    conn.commit()


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
    
    Returns:
        dict: Resumo padronizado (sucesso, mensagem, novos_registos, linhas_aceites, linhas_rejeitadas, erros).
    """
    # 1. Leitura inicial do CSV bruto (sem raise descontrolado)
    try:
        df_raw = pd.read_csv(io.BytesIO(conteudo_bytes))
    except Exception as e:
        return {
            "sucesso": False,
            "mensagem": f"Não foi possível ler o ficheiro CSV enviado: {str(e)}",
            "novos_registos": 0,
            "linhas_aceites": 0,
            "linhas_rejeitadas": 0,
            "erros": [str(e)]
        }

    if df_raw.empty:
        return {
            "sucesso": False,
            "mensagem": "O ficheiro CSV enviado está vazio.",
            "novos_registos": 0,
            "linhas_aceites": 0,
            "linhas_rejeitadas": 0,
            "erros": ["Ficheiro CSV sem linhas de dados."]
        }

    # 2. Processamento universal via gps_processor
    try:
        df_proc = calcular_metricas_completas(df_raw, anonimizar=anonimizar)
    except Exception as e:
        return {
            "sucesso": False,
            "mensagem": f"Erro ao processar a estrutura do CSV: {str(e)}",
            "novos_registos": 0,
            "linhas_aceites": 0,
            "linhas_rejeitadas": len(df_raw),
            "erros": [str(e)]
        }

    # Verificação estrita de colunas obrigatórias
    colunas_obrigatorias = ['date', 'player_name', 'distance_m', 'duration_min', 'player_load', 'top_speed_kmh']
    colunas_faltantes = [c for c in colunas_obrigatorias if c not in df_proc.columns]

    if colunas_faltantes or df_proc['player_name'].dropna().empty:
        msg_erro = f"Ficheiro CSV inválido: colunas obrigatórias ausentes ({', '.join(colunas_faltantes)})." if colunas_faltantes else "Coluna 'player_name' ausente ou totalmente vazia."
        return {
            "sucesso": False,
            "mensagem": msg_erro,
            "novos_registos": 0,
            "linhas_aceites": 0,
            "linhas_rejeitadas": len(df_raw),
            "erros": [msg_erro]
        }

    # 3. FASE DE VALIDAÇÃO PRÉVIA (Fail-Fast: Se houver erros de integridade, rejeita o ficheiro)
    erros_validacao = []
    
    for idx, row in df_proc.iterrows():
        num_linha = idx + 2

        # Validar Nome
        val_atleta = row.get("player_name")
        nome_real = str(val_atleta).strip() if pd.notnull(val_atleta) else ""
        if not nome_real or nome_real.lower() in ["nan", "none", "n/d", "a00"]:
            erros_validacao.append(f"Linha {num_linha}: Nome de atleta ausente ou inválido.")

        # Validar Data
        val_data = row.get("date")
        data_dt = pd.to_datetime(val_data, errors='coerce') if pd.notnull(val_data) else pd.NaT
        if pd.isna(data_dt):
            erros_validacao.append(f"Linha {num_linha}: Data de sessão ausente ou inválida.")

        # Validar Métricas Negativas
        distancia = safe_float(row.get("distance_m"))
        duracao = safe_float(row.get("duration_min"))
        player_load = safe_float(row.get("player_load"))
        top_speed = safe_float(row.get("top_speed_kmh"))
        hsr = safe_float(row.get("hsr_m"))
        sprint = safe_float(row.get("sprint_m"))

        metricas_checagem = [m for m in [distancia, duracao, player_load, top_speed, hsr, sprint] if m is not None]
        if any(m < 0 for m in metricas_checagem):
            erros_validacao.append(f"Linha {num_linha}: Métricas físicas com valores negativos para '{nome_real}'.")

    # Se forem detetados erros de validação, aborta sem gravar na BD
    if erros_validacao:
        return {
            "sucesso": False,
            "mensagem": f"Ficheiro rejeitado: {len(erros_validacao)} erro(s) de validação detetado(s).",
            "novos_registos": 0,
            "linhas_aceites": 0,
            "linhas_rejeitadas": len(df_proc),
            "erros": erros_validacao
        }

    # 4. GRAVAÇÃO EM BD (Transação Atémica)
    conn = get_db_connection(db_path)
    garantir_tabelas_db(conn)
    cursor = conn.cursor()

    linhas_aceites = 0
    linhas_rejeitadas = 0
    novos_registos = 0
    erros = []
    registos_sincronizacao = []

    try:
        for idx, row in df_proc.iterrows():
            num_linha = idx + 2

            nome_real = str(row.get("player_name")).strip()
            data_dt = pd.to_datetime(row.get("date"))
            data_sessao_str = data_dt.strftime("%Y-%m-%d")

            distancia = safe_float(row.get("distance_m"))
            duracao = safe_float(row.get("duration_min"))
            player_load = safe_float(row.get("player_load"))
            top_speed = safe_float(row.get("top_speed_kmh"))
            hsr = safe_float(row.get("hsr_m"))
            
            # Sem inventar "MD" fictício se o campo estiver ausente
            val_mc = row.get("microcycle_day")
            microcycle = str(val_mc).strip() if pd.notnull(val_mc) and str(val_mc).strip() != "" else None

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

            # Persistência Relacional
            jogador_id, _ = obter_ou_criar_jogador(cursor, nome_real)
            tipo_sessao = microcycle if microcycle else "Treino Principal"
            sessao_id = obter_ou_criar_sessao(cursor, data_sessao_str, tipo_sessao)

            # Verificação de Duplicação
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

        # 5. Sincronização do CSV unificado
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
        return {
            "sucesso": False,
            "mensagem": f"Erro interno ao gravar na base de dados: {str(e)}",
            "novos_registos": 0,
            "linhas_aceites": 0,
            "linhas_rejeitadas": len(df_proc),
            "erros": [str(e)]
        }
    finally:
        conn.close()

    return {
        "sucesso": True,
        "mensagem": f"Importação concluída com sucesso. {novos_registos} novos registos importados.",
        "novos_registos": novos_registos,
        "linhas_aceites": linhas_aceites,
        "linhas_rejeitadas": linhas_rejeitadas,
        "erros": erros
    }