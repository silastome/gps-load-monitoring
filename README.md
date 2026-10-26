# GPS Load Monitoring Web Application

Aplicação web modular para ingestão, análise e monitorização de carga física de atletas a partir de ficheiros GPS, desenvolvida no âmbito da **UFCD 5425 — Projeto de Tecnologias e Programação de Sistemas de Informação** (IEFP).

## 🚀 Tecnologias Utilizadas
- **Linguagem:** Python 3.10+
- **Framework Web:** FastAPI + Uvicorn
- **Base de Dados:** SQLite3 (Modelo Relacional 3FN)
- **Processamento de Dados:** Pandas
- **Frontend:** Jinja2, Tailwind CSS, Chart.js

## 📐 Arquitetura da Aplicação (3 Camadas)
- `web/`: Rotas HTTP FastAPI e renderização Jinja2/Tailwind.
- `services/`: Ingestão CSV, validação estrita (RN03) e cálculo de métricas (`upload_service.py`).
- `repositories/`: Camada de persistência e acesso à base de dados SQLite.

## 🛠️ Como Executar Localmente
1. `git clone https://github.com/silastome/gps-load-monitoring.git`
2. `cd gps-load-monitoring`
3. `pip install fastapi uvicorn pandas jinja2 python-multipart`
4. `PYTHONPATH=. python3 -m uvicorn web.app:app --reload --port 8000`

## 📜 Licença e Contexto
Projeto desenvolvido por **Silas Tomé** sob orientação do Formador **Rúben Ferreira** para a UFCD 5425 (IEFP Faro).
