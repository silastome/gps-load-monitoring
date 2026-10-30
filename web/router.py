import os
import io
import pandas as pd
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.gps_processor import calcular_metricas_completas
from dashboard.graficos import (
    fig_ranking_bar,
    fig_perfil_mecanico,
    fig_quadrantes_volume_intensidade,
    fig_vel_vs_acc,
    fig_radar_comparison,
    fig_normalized_bar_comparison
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "erro": None})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    data_sessao: str = Query(None),
    p1: str = Query("A01"),
    p2: str = Query("Mediana da Equipa")
):
    csv_dash = OUT_DIR / "conversao_dash_final.csv"
    
    if not csv_dash.exists():
        return RedirectResponse(url="/", status_code=303)

    df_full = pd.read_csv(csv_dash)
    df_full["date"] = pd.to_datetime(df_full["date"], errors="coerce")

    datas_disponiveis = [d.strftime("%Y-%m-%d") for d in df_full["date"].dropna().dt.date.unique()]
    datas_disponiveis.sort(reverse=True)

    if data_sessao and data_sessao in datas_disponiveis:
        df_view = df_full[df_full["date"].dt.strftime("%Y-%m-%d") == data_sessao].copy()
        sessao_ativa = data_sessao
    else:
        df_view = df_full.copy()
        sessao_ativa = "Todas as Sessões"

    df_active = df_view[df_view["distance_m"] > 0]
    atletas_disponiveis = sorted(df_view["player_name"].dropna().unique().tolist())

    if p1 not in atletas_disponiveis and atletas_disponiveis:
        p1 = atletas_disponiveis[0]

    dist_media = df_active["distance_m"].mean() if not df_active.empty else 0
    pl_medio = df_active["player_load"].mean() if not df_active.empty else 0
    vmax_pico = df_active["top_speed_kmh"].max() if not df_active.empty else 0
    dur_media = df_active["duration_min"].mean() if not df_active.empty else 0

    meta = {
        "n_obs": int(len(df_active)),
        "n_atletas": int(df_active["player_name"].nunique()),
        "dist_media": round(float(dist_media), 0),
        "pl_medio": round(float(pl_medio), 1),
        "vmax_pico": round(float(vmax_pico), 1),
        "dur_media": round(float(dur_media), 0),
        "sessao_ativa": sessao_ativa,
        "p1": p1,
        "p2": p2,
        "datas_disponiveis": datas_disponiveis,
        "atletas_disponiveis": atletas_disponiveis
    }

    f_dist = fig_ranking_bar(df_view, 'distance_m', 'Distância Total por Atleta (m)', 'Distância (m)', 'm', '#0072B2')
    f_pl = fig_ranking_bar(df_view, 'player_load', 'Player Load por Atleta', 'Player Load (U.A.)', 'U.A.', '#56B4E9')
    f_vmax = fig_ranking_bar(df_view, 'top_speed_kmh', 'Velocidade Máxima (km/h)', 'V. Máxima (km/h)', 'km/h', '#d97706')
    f_int = fig_ranking_bar(df_view, 'distance_per_min', 'Intensidade de Treino (m/min)', 'Intensidade (m/min)', 'm/min', '#009E73')
    f_mec = fig_perfil_mecanico(df_view)

    f_quad = fig_quadrantes_volume_intensidade(df_view)
    f_vel_acc = fig_vel_vs_acc(df_view)

    f_radar = fig_radar_comparison(df_view, p1, p2)
    f_norm_bar = fig_normalized_bar_comparison(df_view, p1, p2)

    cols_tabela = ['player_name', 'duration_min', 'distance_m', 'player_load', 'top_speed_kmh', 'distance_per_min']
    cols_presentes = [c for c in cols_tabela if c in df_view.columns]
    
    tabela_df = df_view[cols_presentes].copy()
    tabela_df = tabela_df.round(1)
    
    tabela_registos = []
    for _, r in tabela_df.iterrows():
        is_active = r.get('distance_m', 0) > 0
        tabela_registos.append({
            'player_name': r['player_name'],
            'duration_min': r['duration_min'] if is_active else '-',
            'distance_m': r['distance_m'] if is_active else '-',
            'player_load': r['player_load'] if is_active else '-',
            'top_speed_kmh': r['top_speed_kmh'] if is_active else '-',
            'distance_per_min': r['distance_per_min'] if is_active else 'Sem Registo'
        })

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "meta": meta,
            "tabela_registos": tabela_registos,
            "fig_dist_json": f_dist.to_json(),
            "fig_pl_json": f_pl.to_json(),
            "fig_vmax_json": f_vmax.to_json(),
            "fig_int_json": f_int.to_json(),
            "fig_mec_json": f_mec.to_json(),
            "fig_quad_json": f_quad.to_json(),
            "fig_vel_acc_json": f_vel_acc.to_json(),
            "fig_radar_json": f_radar.to_json(),
            "fig_norm_bar_json": f_norm_bar.to_json(),
        }
    )


@router.post("/upload")
async def process_upload(request: Request, file: UploadFile = File(...)):
    try:
        conteudo = await file.read()
        df_raw = pd.read_csv(io.BytesIO(conteudo))

        df_processado = calcular_metricas_completas(df_raw)

        os.makedirs(OUT_DIR, exist_ok=True)
        df_processado.to_csv(OUT_DIR / "conversao_dash_final.csv", index=False)

        return RedirectResponse(url="/dashboard", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("upload.html", {"request": request, "erro": f"Erro ao processar ficheiro: {str(e)}"})
