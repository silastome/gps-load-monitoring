# ⚽ GPS Load Monitoring App

Aplicação web desenvolvida em FastAPI e SQLite para ingestão, processamento e visualização de dados de carga interna/externa de atletas recolhidos via GPS.

> Nota: Projeto desenvolvido no âmbito do módulo UFCD 5425 (IEFP).

---

## 🚀 Funcionalidades

- Ingestão de Dados: Upload e parsing automático de ficheiros CSV de sessões de treino.
- Base de Dados Relacional: Persistência de atletas, sessões e registos em SQLite.
- Dashboard Interativo: Interface em Jinja2, Tailwind CSS e Chart.js.
- Arquitetura em Camadas: Organização separando Repositories, Services e Web App.

---

## 🛠️ Tecnologias Utilizadas

- Backend: Python 3, FastAPI, Uvicorn
- Base de Dados: SQLite3
- Manipulação de Dados: Pandas
- Frontend: Jinja2 Templates, Tailwind CSS, JavaScript

---

## ⚙️ Como Executar Localmente

1. Clonar o repositório:
   git clone https://github.com/silastome/gps-load-monitoring.git
   cd gps-load-monitoring

2. Instalar dependências:
   pip install fastapi uvicorn pandas jinja2 python-multipart

3. Iniciar a aplicação:
   PYTHONPATH=. python3 -m uvicorn web.app:app --port 8000

4. Aceder no navegador:
   http://127.0.0.1:8000
