"""
===============================================================================
ROUTER DE ROTAS E ENDPOINTS WEB (FASTAPI)
===============================================================================
Descrição: Define as rotas do dashboard web, realizando a extração e a 
           estruturação dos dados relacionais do SQLite/CSV para o template 
           v5_Elite, além de gerir o upload e o reset da base de dados.
===============================================================================
"""

import io
import os
import json
from pathlib import Path
import pandas as pd
import numpy as np

from fastapi import APIRouter, Request, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.upload_service import processar_csv_upload
from dashboard.leitura import carregar_dashboard
from dashboard.metricas import gerar_insights_sessao, extrair_ficha_atleta
from dashboard.graficos import (
    fig_ranking_bar,
    fig_perfil_mecanico,
    fig_quadrantes_volume_intensidade,
    fig_vel_vs_acc,
    fig_acwr_longitudinal,
    fig_fases_microciclo,
    fig_foster_longitudinal,
    fig_radar_comparison,
    fig_normalized_bar_comparison
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


def estruturar_sessoes_json(df_full: pd.DataFrame) -> str:
    """Converte o DataFrame completo num JSON estruturado por data e atleta para o v5_Elite."""
    if df_full is None or df_full.empty or "date" not in df_full.columns:
        return "{}"

    df_copy = df_full.copy()
    df_copy['date_str'] = pd.to_datetime(df_copy['date']).dt.strftime('%Y-%m-%d')
    base_sessoes = {}

    for data_str, group in df_copy.groupby('date_str'):
        atletas = []
        for _, row in group.iterrows():
            rsei_val = float(row.get('rsei_individual', row.get('rsei', 0.0))) if pd.notna(row.get('rsei_individual', row.get('rsei'))) else 0.0
            ietj_val = float(row.get('ietj', 80.0)) if pd.notna(row.get('ietj')) else 80.0
            
            # Alerta se RSEI > 1.05 ou zona de risco no ACWR
            alertas_val = 1 if (rsei_val > 1.05 or row.get('acwr_zone') == 'Spike Zone (>1.50)') else 0

            atleta_obj = {
                "id": str(row.get('player_name', 'Atleta')),
                "pos": str(row.get('posicao', row.get('Posicao', 'Plantel'))),
                "dist": round(float(row.get('distance_m', 0.0)), 1) if pd.notna(row.get('distance_m')) else 0.0,
                "pl": round(float(row.get('player_load', 0.0)), 1) if pd.notna(row.get('player_load')) else 0.0,
                "vmax": round(float(row.get('top_speed_kmh', 0.0)), 1) if pd.notna(row.get('top_speed_kmh')) else 0.0,
                "int": round(float(row.get('distance_per_min', 0.0)), 1) if pd.notna(row.get('distance_per_min')) else 0.0,
                "accel": round(float(row.get('max_acceleration', 0.0)), 2) if pd.notna(row.get('max_acceleration')) else 0.0,
                "desacel": round(float(row.get('max_deceleration', 0.0)), 2) if pd.notna(row.get('max_deceleration')) else 0.0,
                "rsei": round(rsei_val, 3),
                "ietj": round(ietj_val, 1),
                "alertas": alertas_val
            }
            atletas.append(atleta_obj)
        
        base_sessoes[data_str] = atletas

    return json.dumps(base_sessoes, ensure_ascii=False)


@router.get("/", response_class=HTMLResponse)
def upload_page(request: Request):
    """Página inicial para carregamento de ficheiros CSV."""
    return templates.TemplateResponse("upload.html", {"request": request, "erro": None})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    data_sessao: str = Query(None),
    p1: str = Query("A01"),
    p2: str = Query("Mediana da Equipa"),
    aba_ativa: str = Query("tab1")
):
    """Renderiza a interface do dashboard interativo v5_Elite com dados reais."""
    try:
        df_full, _ = carregar_dashboard()
    except Exception:
        return RedirectResponse(url="/", status_code=303)

    if df_full is None or df_full.empty:
        return RedirectResponse(url="/", status_code=303)

    # 1. Serializar todas as sessões para o motor JavaScript do v5_Elite
    sessoes_json = estruturar_sessoes_json(df_full)

    # 2. Datas Disponíveis (Ordenadas da mais recente para a mais antiga)
    if "date" in df_full.columns and not df_full["date"].dropna().empty:
        datas_disponiveis = [d.strftime("%Y-%m-%d") for d in df_full["date"].dropna().dt.date.unique()]
        datas_disponiveis.sort(reverse=True)
    else:
        datas_disponiveis = []

    # 3. Definição da Sessão Ativa
    if data_sessao is None and datas_disponiveis:
        data_sessao = datas_disponiveis[0]

    # 4. Tratamento das Vistas
    if data_sessao and data_sessao in datas_disponiveis:
        df_view = df_full[df_full["date"].dt.strftime("%Y-%m-%d") == data_sessao].copy()
        sessao_ativa = data_sessao
    else:
        sessao_ativa = "Todas as Sessões (Média da Equipa)"
        agg_rules = {}
        for c in ['duration_min', 'distance_m', 'player_load', 'distance_per_min', 'hsr_m', 'sprint_m']:
            if c in df_full.columns:
                agg_rules[c] = 'mean'
        for c in ['top_speed_kmh', 'max_acceleration', 'max_deceleration']:
            if c in df_full.columns:
                agg_rules[c] = 'max'
        
        if agg_rules and 'player_name' in df_full.columns:
            df_view = df_full.groupby('player_name', as_index=False).agg(agg_rules)
        else:
            df_view = df_full.copy()

    if 'player_name' in df_view.columns:
        df_view = df_view.drop_duplicates(subset=['player_name']).copy()

    # 5. Lista de Atletas Disponíveis
    if "player_name" in df_view.columns:
        atletas_disponiveis = sorted(df_view["player_name"].dropna().astype(str).unique().tolist())
    else:
        atletas_disponiveis = []

    if p1 not in atletas_disponiveis and atletas_disponiveis:
        p1 = atletas_disponiveis[0]

    # 6. Registos Ativos e Metadados Globais
    df_active = df_view[df_view["distance_m"] > 0] if "distance_m" in df_view.columns else df_view
    if df_active.empty:
        df_active = df_view

    dist_media = df_active["distance_m"].mean() if "distance_m" in df_active.columns and not df_active["distance_m"].dropna().empty else 0
    pl_medio   = df_active["player_load"].mean() if "player_load" in df_active.columns and not df_active["player_load"].dropna().empty else 0
    vmax_pico  = df_active["top_speed_kmh"].max() if "top_speed_kmh" in df_active.columns and not df_active["top_speed_kmh"].dropna().empty else 0
    dur_media  = df_active["duration_min"].mean() if "duration_min" in df_active.columns and not df_active["duration_min"].dropna().empty else 0

    # 7. Insights Metodológicos & Ficha do Atleta
    insights_lista = gerar_insights_sessao(df_view)
    ficha_atleta_p1 = extrair_ficha_atleta(df_view, p1)

    meta = {
        "n_obs": int(len(df_active)),
        "n_atletas": int(df_active["player_name"].nunique()) if "player_name" in df_active.columns else 0,
        "dist_media": round(float(dist_media), 0) if not pd.isna(dist_media) else 0,
        "pl_medio": round(float(pl_medio), 1) if not pd.isna(pl_medio) else 0,
        "vmax_pico": round(float(vmax_pico), 1) if not pd.isna(vmax_pico) else 0,
        "dur_media": round(float(dur_media), 0) if not pd.isna(dur_media) else 0,
        "sessao_ativa": sessao_ativa,
        "p1": p1,
        "p2": p2,
        "aba_ativa": aba_ativa,
        "datas_disponiveis": datas_disponiveis,
        "atletas_disponiveis": atletas_disponiveis
    }

    # 8. Geração de Gráficos
    f_dist = fig_ranking_bar(df_view, 'distance_m', 'Distância Total por Atleta (m)', 'Distância (m)', 'm', '#0072B2')
    f_pl   = fig_ranking_bar(df_view, 'player_load', 'Player Load por Atleta', 'Player Load (U.A.)', 'U.A.', '#56B4E9')
    f_vmax = fig_ranking_bar(df_view, 'top_speed_kmh', 'Velocidade Máxima (km/h)', 'V. Máxima (km/h)', 'km/h', '#d97706')
    f_int  = fig_ranking_bar(df_view, 'distance_per_min', 'Intensidade de Treino (m/min)', 'Intensidade (m/min)', 'm/min', '#009E73')
    f_mec  = fig_perfil_mecanico(df_view)

    f_quad    = fig_quadrantes_volume_intensidade(df_view)
    f_vel_acc = fig_vel_vs_acc(df_view)

    f_acwr   = fig_acwr_longitudinal(df_full, p1)
    f_fases  = fig_fases_microciclo(df_full)
    f_foster = fig_foster_longitudinal(df_full, p1)

    f_radar    = fig_radar_comparison(df_view, p1, p2)
    f_norm_bar = fig_normalized_bar_comparison(df_view, p1, p2)

    # 9. Tabela de Registos
    tabela_registos = []
    if 'player_name' in df_view.columns:
        for _, r in df_view.iterrows():
            dist_val = r.get('distance_m', 0)
            is_valid = pd.notnull(dist_val) and dist_val > 0
            
            def fmt(val, dec=1):
                if pd.notnull(val) and is_valid:
                    try:
                        return f"{float(val):.{dec}f}"
                    except (ValueError, TypeError):
                        return "-"
                return "-"

            tabela_registos.append({
                'player_name': str(r.get('player_name', 'A00')),
                'duration_min': fmt(r.get('duration_min'), 0),
                'distance_m': fmt(r.get('distance_m'), 0),
                'player_load': fmt(r.get('player_load'), 1),
                'top_speed_kmh': fmt(r.get('top_speed_kmh'), 1),
                'distance_per_min': fmt(r.get('distance_per_min'), 1) if is_valid else 'Sem Registo'
            })

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "meta": meta,
            "sessoes_json": sessoes_json,
            "insights": insights_lista,
            "ficha_atleta": ficha_atleta_p1,
            "tabela_registos": tabela_registos,
            "fig_dist_json": f_dist.to_json(),
            "fig_pl_json": f_pl.to_json(),
            "fig_vmax_json": f_vmax.to_json(),
            "fig_int_json": f_int.to_json(),
            "fig_mec_json": f_mec.to_json(),
            "fig_quad_json": f_quad.to_json(),
            "fig_vel_acc_json": f_vel_acc.to_json(),
            "fig_acwr_json": f_acwr.to_json(),
            "fig_fases_json": f_fases.to_json(),
            "fig_foster_json": f_foster.to_json(),
            "fig_radar_json": f_radar.to_json(),
            "fig_norm_bar_json": f_norm_bar.to_json(),
        }
    )


@router.post("/upload")
async def process_upload(request: Request, file: UploadFile = File(...)):
    """Processa o upload do CSV de forma assíncrona."""
    try:
        conteudo_bytes = await file.read()
        res = processar_csv_upload(conteudo_bytes)

        if not res.get("sucesso", True):
            return templates.TemplateResponse(
                "upload.html",
                {
                    "request": request,
                    "erro": res.get("mensagem", "Erro ao processar o ficheiro CSV."),
                    "erros_detalhe": res.get("erros", [])
                }
            )

        return RedirectResponse(url="/dashboard", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(
            "upload.html", 
            {"request": request, "erro": f"Erro inesperado ao processar ficheiro: {str(e)}"}
        )


@router.post("/reset")
def reset_db():
    """Repõe o estado limpo da base de dados SQLite."""
    try:
        from repositories import get_db_connection
        from repositories.registos_repo import limpar_base_dados
        conn = get_db_connection()
        limpar_base_dados(conn)
        conn.close()
    except Exception:
        pass
    return RedirectResponse(url="/", status_code=303)