"""
===============================================================================
APLICAÇÃO PRINCIPAL FASTAPI E INICIALIZAÇÃO DE INFRAESTRUTURA
===============================================================================
Descrição: Instancia a aplicação FastAPI, inicializa o esquema da base de dados
           SQLite no arranque (schema.sql) e inclui o router de rotas web.
===============================================================================
"""

import os
from pathlib import Path
from fastapi import FastAPI
from repositories import get_db_connection
from web.router import router

BASE_DIR = Path(__file__).resolve().parent.parent


def create_app() -> FastAPI:
    """Fábrica de criação e configuração da aplicação FastAPI."""
    app = FastAPI(
        title="Sistema de Monitorização de Carga GPS",
        description="Plataforma Universal e Agnostic White-Label para Monitorização de Carga GPS no Futebol",
        version="1.0.0"
    )

    @app.on_event("startup")
    def startup_event():
        """Verifica e executa o schema.sql para garantir a estrutura do SQLite."""
        try:
            conn = get_db_connection()
            schema_path = BASE_DIR / "docs" / "schema.sql"
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            conn.close()
        except Exception as e:
            print(f"Aviso no arranque da base de dados: {e}")

    # Inclusão do router centralizado de rotas
    app.include_router(router)

    return app


app = create_app()