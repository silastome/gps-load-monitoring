"""
===============================================================================
PONTO DE ENTRADA DA APLICAÇÃO FASTAPI (MAIN.PY) COM LOGGING EM FICHEIRO
===============================================================================
"""

import logging
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from web.router import router

# Configuração do Logger Principal (grava simultaneamente em app.log e na consola)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("app.log", mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("gps-load-monitoring")
logger.info("Servidor GPS Load Monitoring a iniciar...")

app = FastAPI(
    title="Sistema de Monitorização de Carga GPS",
    description="Projeto de Tecnologias e Programação de Sistemas de Informação (UFCD 5425)",
    version="1.0.0"
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)