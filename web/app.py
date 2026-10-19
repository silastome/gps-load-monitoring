import sys
import os

# Adiciona o diretorio raiz do projeto (ufcd5425_gps_app) ao sys.path do Python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from repositories import init_db, get_connection
from repositories.jogadores_repo import get_todos_jogadores
from services.upload_service import processar_e_ingestao_csv

TEMPLATES_DIR = os.path.join(BASE_DIR, "web", "templates")

app = FastAPI(title="UFCD 5425 - Monitorização de Carga GPS", version="1.0.0")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def dashboard_principal(request: Request):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_registos FROM registos")
        total_r = cursor.fetchone()["total_registos"]
        cursor.execute("SELECT COUNT(*) as total_jogadores FROM jogadores")
        total_j = cursor.fetchone()["total_jogadores"]
        cursor.execute("SELECT COUNT(*) as total_sessoes FROM sessoes")
        total_s = cursor.fetchone()["total_sessoes"]
        
        resumo = {"total_registos": total_r, "total_jogadores": total_j, "total_sessoes": total_s}
        
    jogadores = get_todos_jogadores()
    return templates.TemplateResponse("index.html", {"request": request, "resumo": resumo, "jogadores": jogadores})

@app.get("/api/jogadores")
def listar_jogadores():
    return get_todos_jogadores()

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Apenas ficheiros .csv são permitidos.")
    conteudo = await file.read()
    try:
        resultado = processar_e_ingestao_csv(conteudo)
        return JSONResponse(content={"status": "sucesso", "dados": resultado})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
