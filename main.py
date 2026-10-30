import uvicorn
from fastapi import FastAPI
from web.router import router

app = FastAPI(
    title="Sistema de Monitorização de Carga GPS",
    description="Projeto de Tecnologias e Programação de Sistemas de Informação (UFCD 5425)",
    version="1.0.0"
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
