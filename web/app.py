import os
import json
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from repositories import get_db_connection
from repositories.jogadores_repo import listar_jogadores
from repositories.registos_repo import obter_totais_dashboard, obter_dados_graficos, limpar_base_dados
from services.upload_service import processar_csv_upload

app = FastAPI(title="GPS Load Monitoring")

base_dir = os.path.dirname(__file__)
template_dir = os.path.join(base_dir, "templates")
templates = Jinja2Templates(directory=template_dir)

@app.on_event("startup")
def startup():
    conn = get_db_connection()
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.close()

@app.get("/")
def dashboard(request: Request):
    conn = get_db_connection()
    totais = obter_totais_dashboard(conn)
    jogadores = listar_jogadores(conn)
    graficos = obter_dados_graficos(conn)
    conn.close()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "totais": totais,
        "jogadores": jogadores,
        "graficos_json": json.dumps(graficos),
        "resumo": None,
        "erro": None
    })

@app.post("/upload")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    conteudo = await file.read()
    resumo = None
    mensagem_erro = None
    
    try:
        resumo = processar_csv_upload(conteudo)
    except Exception as e:
        mensagem_erro = str(e)

    conn = get_db_connection()
    totais = obter_totais_dashboard(conn)
    jogadores = listar_jogadores(conn)
    graficos = obter_dados_graficos(conn)
    conn.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "totais": totais,
        "jogadores": jogadores,
        "graficos_json": json.dumps(graficos),
        "resumo": resumo,
        "erro": mensagem_erro
    })

@app.post("/reset")
def reset_db():
    conn = get_db_connection()
    limpar_base_dados(conn)
    conn.close()
    return RedirectResponse(url="/", status_code=303)
