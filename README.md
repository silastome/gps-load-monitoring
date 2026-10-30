# Sistema de Monitorização e Análise de Carga GPS de Atletas

Aplicação web desenvolvida no âmbito da **UFCD 5425 - Projeto de Tecnologias e Programação de Sistemas de Informação** (IEFP).

## 🚀 Funcionalidades Principais

- **Ingestão e Validação Universal de CSV:** Suporte a ficheiros exportados por sistemas GPS (STATSports Apex, Catapult, Wimu, Oliver, etc.).
- **Filtragem Inteligente de Sub-Splits:** Extração automática de sessões globais (`split_name == 'all'`), evitando duplicação de dados.
- **Anonimização de Atletas:** Mapeamento automático de nomes para identificadores anónimos (`A01`, `A02`, `A03`...) em conformidade com o RGPD.
- **Dashboard Operacional Multidimensionais (Navegação por Abas):**
  - **📍 Sessão GPS:** Rankings ordenados de Distância, Player Load, Velocidade Máxima, Intensidade (m/min) e Perfil Mecânico.
  - **📊 Matriz & Perfis de Carga:** Quadrantes de Volume vs. Intensidade e Perfil Neuromuscular (km/h vs. m/s²).
  - **👥 Comparador de Atletas:** Gráfico Radar/Teia e barras de desvio relativo (100% = Média da Equipa) para análise entre atletas ou contra a mediana do plantel.
  - **📋 Tabela de Registos:** Matriz com valores numéricos individuais exatos.

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.7+, FastAPI, Uvicorn
- **Processamento de Dados:** Pandas, NumPy
- **Visualização de Dados:** Plotly JavaScript
- **Frontend / Interface:** HTML5, CSS3 (Dark Theme), Jinja2 Templates
- **Base de Dados:** SQLite (`app.db`)

## 💻 Como Executar

1. Instalar as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Iniciar o servidor web:
   ```bash
   python main.py
   ```

3. Aceder no navegador a `http://127.0.0.1:8000`.
