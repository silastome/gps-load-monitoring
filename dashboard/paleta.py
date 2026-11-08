"""
===============================================================================
MÓDULO DE PALETA DE CORES E CONSTANTES VISUAIS (OKABE-ITO)
===============================================================================
Descrição: Define as constantes visuais universais, escalas de mapa de calor e
           dicionários de mapeamento por fase de microciclo e zona de risco.
===============================================================================
"""

# Paleta Acessível Okabe-Ito (Color Vision Deficiency - CVD Compliant)
OKABE_ITO = {
    "blue":      "#0072B2",
    "orange":    "#E69F00",
    "green":     "#009E73",
    "red":       "#D55E00",
    "purple":    "#CC79A7",
    "yellow":    "#F0E442",
    "skyblue":   "#56B4E9",
    "black":     "#000000",
    "gray":      "#999999",
    "darkblue":  "#003366",
    "white":     "#FFFFFF",
    "lightgray": "#F5F5F5",
}

# Escala Contínua para Plotly (Divergente: Azul -> Branco -> Laranja/Vermelho)
HEATMAP_SCALE = [
    [0.0,  "#0072B2"],
    [0.25, "#56B4E9"],
    [0.5,  "#FFFFFF"],
    [0.75, "#E69F00"],
    [1.0,  "#D55E00"],
]

# Cores de Agrupamento Dinâmico (Clusters C1 a C4)
CLUSTER_COLORS = ["#0072B2", "#56B4E9", "#E69F00", "#D55E00"]

# Mapeamento de Cores por Fase do Microciclo (Periodização Tática)
FASE_COLORS = {
    "MD-4":             "#0072B2",
    "MD-3":             "#56B4E9",
    "MD-2":             "#009E73",
    "MD-1":             "#F0E442",
    "MD":               "#D55E00",
    "MD+1":             "#CC79A7",
    "Outro/Transição":  "#999999",
    "Outro/Transicao":  "#999999",
}

# Mapeamento de Zonas de Risco de ACWR (EWMA)
ACWR_ZONE_COLORS = {
    "Subtreino (< 0.80)":         "#56B4E9",
    "Sweet Spot (0.80 - 1.30)":   "#009E73",
    "Carga Elevada (1.30 - 1.50)":"#E69F00",
    "Risco Elevado (> 1.50)":     "#D55E00",
}

# Cores Base de Layout (Dark Theme UI)
BG_DARK  = "#0f172a"
BG_PANEL = "#1e293b"
BG_LINE  = "#334155"
TEXT     = "#e2e8f0"
TEXT_DIM = "#94a3b8"


def obter_cor_fase(fase: str) -> str:
    """Devolve a cor correspondente à fase do microciclo com fallback defensivo."""
    if not fase:
        return OKABE_ITO["gray"]
    return FASE_COLORS.get(str(fase).strip(), OKABE_ITO["gray"])


def obter_cor_acwr(zona: str) -> str:
    """Devolve a cor correspondente à zona de risco de ACWR com fallback defensivo."""
    if not zona:
        return OKABE_ITO["gray"]
    return ACWR_ZONE_COLORS.get(str(zona).strip(), OKABE_ITO["gray"])