from fastapi import FastAPI, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from repositories import get_db_connection, reset_db
from services.upload_service import processar_csv_upload

app = FastAPI(title="GPS Load Monitoring — UFCD 5425")
templates = Jinja2Templates(directory="web/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, msg: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    total_registos = cursor.execute("SELECT COUNT(*) FROM registos").fetchone()[0]

    if total_registos == 0:
        conn.close()
        return templates.TemplateResponse("upload.html", {"request": request, "msg": msg})

    total_atletas = cursor.execute("SELECT COUNT(DISTINCT jogador_id) FROM registos").fetchone()[0]
    total_sessoes = cursor.execute("SELECT COUNT(DISTINCT sessao_id) FROM registos").fetchone()[0]
    ietj_medio = round(cursor.execute("SELECT AVG(ietj) FROM registos").fetchone()[0] or 0, 1)
    rsei_medio = round(cursor.execute("SELECT AVG(rsei) FROM registos").fetchone()[0] or 0, 2)

    # 1. Métricas por Atleta
    stats = cursor.execute("""
        SELECT j.nome, 
               ROUND(AVG(r.ietj), 1) as ietj_avg,
               ROUND(AVG(r.player_load), 1) as load_avg, 
               ROUND(AVG(r.distancia_m), 1) as dist_avg, 
               ROUND(MAX(r.top_speed_kmh), 1) as speed_max,
               ROUND(AVG(r.hsr_m), 1) as hsr_avg
        FROM registos r
        JOIN jogadores j ON j.id = r.jogador_id
        GROUP BY j.id
        ORDER BY j.nome ASC
    """).fetchall()

    chart_labels = [s[0] for s in stats]
    chart_ietj = [s[1] for s in stats]
    chart_load = [s[2] for s in stats]
    chart_dist = [s[3] for s in stats]
    chart_speed = [s[4] for s in stats]
    chart_hsr = [s[5] for s in stats]

    # 2. Perfil do Microciclo
    md_stats = cursor.execute("""
        SELECT microcycle_day,
               ROUND(AVG(player_load), 1),
               ROUND(AVG(ietj), 1),
               ROUND(AVG(distancia_m), 1)
        FROM registos
        GROUP BY microcycle_day
        ORDER BY CASE microcycle_day
            WHEN 'MD-5' THEN 1
            WHEN 'MD-4' THEN 2
            WHEN 'MD-3' THEN 3
            WHEN 'MD-2' THEN 4
            WHEN 'MD-1' THEN 5
            WHEN 'MD'   THEN 6
            ELSE 7 END
    """).fetchall()

    md_labels = [m[0] for m in md_stats]
    md_load = [m[1] for m in md_stats]
    md_ietj = [m[2] for m in md_stats]

    # 3. Tabela Consolidada por Atleta
    atletas_detalhe = cursor.execute("""
        SELECT j.nome, 
               COUNT(r.id) as sessoes, 
               ROUND(AVG(r.distancia_m), 1), 
               ROUND(AVG(r.player_load), 1), 
               ROUND(AVG(r.ietj), 1),
               ROUND(AVG(r.rsei), 2),
               ROUND(MAX(r.top_speed_kmh), 1),
               ROUND(AVG(r.hsr_m), 1)
        FROM jogadores j
        JOIN registos r ON j.id = r.jogador_id
        GROUP BY j.id
        ORDER BY j.nome ASC
    """).fetchall()

    conn.close()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_registos": total_registos,
        "total_atletas": total_atletas,
        "total_sessoes": total_sessoes,
        "ietj_medio": ietj_medio,
        "rsei_medio": rsei_medio,
        "chart_labels": chart_labels,
        "chart_ietj": chart_ietj,
        "chart_load": chart_load,
        "chart_dist": chart_dist,
        "chart_speed": chart_speed,
        "chart_hsr": chart_hsr,
        "md_labels": md_labels,
        "md_load": md_load,
        "md_ietj": md_ietj,
        "atletas": atletas_detalhe,
        "msg": msg
    })

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    contents = await file.read()
    res = processar_csv_upload(contents)
    novos = res.get("novos_registos", 0)
    mensagem = f"CSV importado com sucesso! {novos} registos analisados."
    return RedirectResponse(url=f"/?msg={mensagem}", status_code=303)

@app.get("/reset")
async def reset_dados():
    reset_db()
    return RedirectResponse(url="/?msg=Base%20de%20dados%20limpa.", status_code=303)