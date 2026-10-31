"""
===============================================================================
ROUTER DE ROTAS E ENDPOINTS WEB (FASTAPI)
===============================================================================
Descrição: Define as rotas do dashboard web, realizando o filtro por data
           específica (Ponto 2.1) e a agregação limpa por atleta para a vista
           longitudinal global (Ponto 2.2).
===============================================================================
"""

import io
import os
from pathlib import Path
import pandas as pd

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
    """Renderiza a interface do dashboard interativo."""
    try:
        df_full, _ = carregar_dashboard()
    except Exception:
        return RedirectResponse(url="/", status_code=303)

    if df_full is None or df_full.empty:
        return RedirectResponse(url="/", status_code=303)

    # 1. Datas Disponíveis (Ordenadas do mais recente para o mais antigo)
    if "date" in df_full.columns and not df_full["date"].dropna().empty:
        datas_disponiveis = [d.strftime("%Y-%m-%d") for d in df_full["date"].dropna().dt.date.unique()]
        datas_disponiveis.sort(reverse=True)
    else:
        datas_disponiveis = []

    # 2. Definição da Sessão Ativa por Padrão (Última Sessão Carregada)
    if data_sessao is None and datas_disponiveis:
        data_sessao = datas_disponiveis[0]

    # 3. Tratamento das Vistas: Sessão Única (Ponto 2.1) vs Agregação Longitudinal (Ponto 2.2)
    if data_sessao and data_sessao in datas_disponiveis:
        # Ponto 2.1: Filtra estritamente a data selecionada (1 registo por atleta)
        df_view = df_full[df_full["date"].dt.strftime("%Y-%m-%d") == data_sessao].copy()
        sessao_ativa = data_sessao
    else:
        # Ponto 2.2: Vista "Todas as Sessões" -> Agrupa por atleta (Média/Máximo)
        # Evita a sobreposição de 1.299 pontos/barras e duplicação de atletas
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

    # Garantir deduplicação estrita por atleta na vista do painel
    if 'player_name' in df_view.columns:
        df_view = df_view.drop_duplicates(subset=['player_name']).copy()

    # 4. Lista de Atletas Disponíveis
    if "player_name" in df_view.columns:
        atletas_disponiveis = sorted(df_view["player_name"].dropna().astype(str).unique().tolist())
    else:
        atletas_disponiveis = []

    if p1 not in atletas_disponiveis and atletas_disponiveis:
        p1 = atletas_disponiveis[0]

    # 5. Registos Ativos
    df_active = df_view[df_view["distance_m"] > 0] if "distance_m" in df_view.columns else df_view
    if df_active.empty:
        df_active = df_view

    # 6. Metadados Globais
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

    # 8. Geração de Gráficos (Vistas agregadas vs Séries temporais históricas df_full)
    f_dist = fig_ranking_bar(df_view, 'distance_m', 'Distância Total por Atleta (m)', 'Distância (m)', 'm', '#0072B2')
    f_pl   = fig_ranking_bar(df_view, 'player_load', 'Player Load por Atleta', 'Player Load (U.A.)', 'U.A.', '#56B4E9')
    f_vmax = fig_ranking_bar(df_view, 'top_speed_kmh', 'Velocidade Máxima (km/h)', 'V. Máxima (km/h)', 'km/h', '#d97706')
    f_int  = fig_ranking_bar(df_view, 'distance_per_min', 'Intensidade de Treino (m/min)', 'Intensidade (m/min)', 'm/min', '#009E73')
    f_mec  = fig_perfil_mecanico(df_view)

    f_quad    = fig_quadrantes_volume_intensidade(df_view)
    f_vel_acc = fig_vel_vs_acc(df_view)

    # Gráficos de Série Temporal usam o df_full completo com todas as datas
    f_acwr   = fig_acwr_longitudinal(df_full, p1)
    f_fases  = fig_fases_microciclo(df_full)
    f_foster = fig_foster_longitudinal(df_full, p1)

    f_radar    = fig_radar_comparison(df_view, p1, p2)
    f_norm_bar = fig_normalized_bar_comparison(df_view, p1, p2)

    # 9. Tabela de Registos (Garante 1 linha por atleta sem repetições)
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
    """Processa o upload do CSV e redireciona para a vista limpa do dashboard."""
    try:
        conteudo_bytes = await file.read()
        res = processar_csv_upload(conteudo_bytes)
        return RedirectResponse(url="/dashboard", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "upload.html", 
            {"request": request, "erro": f"Erro ao processar ficheiro: {str(e)}"}
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