# Sistema de Monitorização de Carga GPS (`gps-load-monitoring`)

Plataforma *white-label* e agnóstica para ingestão de dados brutos de GPS desportivo (STATSports, Catapult One, GPExe, Wimu, Oliver, FieldWiz), normalização de métricas e visualização operacional de carga interna e externa.

---

## 🛠️ Arquitetura do Sistema

* **Backend:** FastAPI (Python 3.7+)
* **Processamento de Dados:** Pandas & NumPy
* **Visualização Interativa:** Plotly.js
* **Persistência de Dados:** SQLite (`app.db`) com repositórios dedicados
* **Interface Web:** Templates Jinja2 + CSS Flexbox/Grid responsivo com tema escuro

---

## 📊 Principais Funcionalidades

1. **Ingestão Universal & Normalização:**
   * Reconhecimento automático de sinonímia de cabeçalhos de múltiplos fornecedores.
   * Conversão automática de unidades (m/min, PL/min, velocidade em km/h).
   * Mapeamento e anonimização 1:1 de atletas (`A01`, `A02`, ...).
   * Deduplicação rigorosa por data de sessão e atleta.

2. **Análise Metodológica & Longitudinal:**
   * **ACWR (Acute:Chronic Workload Ratio):** Cálculo via EWMA (Exponentially Weighted Moving Average) e Rolling Average.
   * **Índices de Foster (1998):** Cálculo de Monotonia e Strain em janelas móveis de 7 dias.
   * **Perfil Neuromuscular & Mecânico:** Relações Vmáx vs Aceleração e Aceleração vs Desaceleração.
   * **Estatística Individual:** Cálculo de Z-Score / MBI (Magnitude-Based Inference) por atleta.

3. **Dashboard Interativo Multi-Aba:**
   * **Aba 1 (Sessão GPS):** Ranking da equipa, perfis mecânicos e picos de intensidade.
   * **Aba 2 (Matriz & Perfis de Carga):** Matriz Locomotora, curva temporal de ACWR, distribuição por fase do microciclo e tendência de Foster.
   * **Aba 3 (Comparador de Atletas):** Gráficos Radar (% do máximo) e desvio relativo em relação à média/mediana do grupo.
   * **Aba 4 (Tabela de Registos):** Tabela executiva de valores brutos por sessão.

4. **Exportação PDF Executiva:**
   * Layout de impressão `@media print` otimizado para formato **A4 Landscape**.
   * Redimensionamento automático dos gráficos SVG Plotly para evitar estoiro de páginas.

---

## 🚀 Como Executar a Aplicação

1. **Ativar o ambiente e instalar dependências:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install uvicorn fastapi pandas plotly jinja2 python-multipart

2. Iniciar o servidor web:
   ```bash
   python3 main.py
   ```

3. Aceder no navegador a `http://127.0.0.1:8000`.
