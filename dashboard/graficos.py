"""
===============================================================================
MÓDULO DE GERAÇÃO DE GRÁFICOS INTERATIVOS (PLOTLY)
===============================================================================
Descrição: Biblioteca universal de visualizações Plotly para análise de carga GPS.
           Inclui rankings, perfis mecânicos/neuromusculares, matrizes locomotoras,
           matriz IETJ vs RSEI, comparadores multidimensionais, curva longitudinal
           de ACWR (EWMA), distribuição por fase do microciclo e Foster.
===============================================================================
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Configuração visual padrão (Dark Theme & Okabe-Ito Accessible Palette)
BG_PANEL = "#1e293b"
BG_LINE  = "#334155"
TEXT     = "#e2e8f0"
TEXT_DIM = "#94a3b8"

COLOR_BLUE   = "#0072B2"
COLOR_ORANGE = "#E69F00"
COLOR_GREEN  = "#009E73"
COLOR_RED    = "#D55E00"
COLOR_SKY    = "#56B4E9"
COLOR_PURPLE = "#CC79A7"


def _layout_base() -> dict:
    """Retorna o layout escuro padrão para todos os gráficos do dashboard."""
    return dict(
        paper_bgcolor=BG_PANEL,
        plot_bgcolor=BG_PANEL,
        font=dict(color=TEXT, family="Segoe UI, sans-serif"),
        margin=dict(l=70, r=80, t=50, b=40),
        xaxis=dict(gridcolor=BG_LINE, zerolinecolor=BG_LINE),
        yaxis=dict(gridcolor=BG_LINE, zerolinecolor=BG_LINE),
    )


def _formatar_nome(nome: str) -> str:
    """Garante que a string do nome do atleta não duplica o rótulo."""
    n = str(nome).strip()
    return n if n.lower().startswith("atleta") else f"Atleta {n}"


# =============================================================================
# ABA 1: SESSÃO GPS & RANKINGS
# =============================================================================
def fig_ranking_bar(df: pd.DataFrame, col: str, title: str, x_label: str, unit: str = "", color: str = COLOR_BLUE) -> go.Figure:
    """Gera um gráfico de barras horizontais ordenado por ranking do atleta."""
    if col not in df.columns or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title=f"<b>{title}Sem Dados</b>")
        return fig

    df_valid = df[df[col] > 0].dropna(subset=[col]).sort_values(col, ascending=True)
    if df_valid.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title=f"<b>{title}Sem Registos Válidos</b>")
        return fig

    colors = [color] * len(df_valid)
    if len(colors) >= 2:
        colors[-1] = COLOR_ORANGE
        colors[0]  = COLOR_SKY

    text_labels = [
        f"{val:.1f} {unit}".strip() if abs(val - round(val)) > 1e-4 else f"{int(round(val))} {unit}".strip()
        for val in df_valid[col]
    ]

    fig = go.Figure(go.Bar(
        x=df_valid[col],
        y=df_valid['player_name'],
        orientation='h',
        marker_color=colors,
        text=text_labels,
        textposition='outside',
        cliponaxis=False
    ))

    media = df_valid[col].mean()
    fig.add_vline(
        x=media, 
        line_dash="dash", 
        line_color=COLOR_RED, 
        annotation_text=f"Média: {media:.1f}{unit}", 
        annotation_position="top right"
    )

    max_x = max(df_valid[col].max() * 1.22, 1.0)
    layout = _layout_base()
    layout.update(
        title=f"<b>{title}</b>",
        xaxis_title=x_label,
        xaxis=dict(range=[0, max_x], gridcolor=BG_LINE),
        yaxis=dict(gridcolor=BG_LINE)
    )
    fig.update_layout(**layout)
    return fig


def fig_perfil_mecanico(df: pd.DataFrame) -> go.Figure:
    """Gera a dispersão Aceleração Máxima vs Desaceleração Máxima."""
    cols_req = ['max_acceleration', 'max_deceleration']
    if not all(c in df.columns for c in cols_req) or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Perfil Mecânico (Acc vs Dec) - Dados Ausentes</b>")
        return fig

    df_valid = df.dropna(subset=cols_req).copy()
    df_valid['max_deceleration'] = df_valid['max_deceleration'].abs()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_valid['max_acceleration'],
        y=df_valid['max_deceleration'],
        mode='markers+text',
        text=df_valid['player_name'],
        textposition="top center",
        marker=dict(size=13, color=COLOR_SKY, line=dict(width=1, color='white')),
        hovertemplate="<b>%{text}</b><br>Acc Máx: %{x:.2f} m/s²<br>Dec Máx: %{y:.2f} m/s²<extra></extra>"
    ))

    med_x = df_valid['max_acceleration'].median() if not df_valid.empty else 0
    med_y = df_valid['max_deceleration'].median() if not df_valid.empty else 0
    fig.add_vline(x=med_x, line_dash="dash", line_color=TEXT_DIM)
    fig.add_hline(y=med_y, line_dash="dash", line_color=TEXT_DIM)

    layout = _layout_base()
    layout.update(
        title="<b>Perfil Mecânico: Aceleração vs Desaceleração Máxima (m/s²)</b>",
        xaxis_title="Aceleração Máxima (m/s²)",
        yaxis_title="Desaceleração Máxima (m/s²)"
    )
    fig.update_layout(**layout)
    return fig


# =============================================================================
# ABA 2: MATRIZ & PERFIS DA CARGA
# =============================================================================
def fig_quadrantes_volume_intensidade(df: pd.DataFrame) -> go.Figure:
    """Matriz Locomotora: Distância Total (Volume) vs Metros/Minuto (Intensidade)."""
    cols_req = ['distance_m', 'distance_per_min']
    if not all(c in df.columns for c in cols_req) or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Matriz Locomotora - Dados Ausentes</b>")
        return fig

    df_valid = df[df['distance_m'] > 0].dropna(subset=cols_req)
    if df_valid.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Matriz Locomotora - Sem Dados Válidos</b>")
        return fig

    color_col = df_valid['player_load'] if 'player_load' in df_valid.columns else df_valid['distance_m']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_valid['distance_m'],
        y=df_valid['distance_per_min'],
        mode='markers+text',
        text=df_valid['player_name'],
        textposition="top center",
        marker=dict(
            size=14, 
            color=color_col, 
            colorscale='Viridis', 
            showscale=True, 
            colorbar=dict(title="Player Load")
        ),
        hovertemplate="<b>%{text}</b><br>Distância: %{x:.0f} m<br>Intensidade: %{y:.1f} m/min<extra></extra>"
    ))

    fig.add_vline(x=df_valid['distance_m'].median(), line_dash="dash", line_color=TEXT_DIM)
    fig.add_hline(y=df_valid['distance_per_min'].median(), line_dash="dash", line_color=TEXT_DIM)

    layout = _layout_base()
    layout.update(
        title="<b>Matriz Locomotora: Volume (Distância) vs Intensidade (m/min)</b>",
        xaxis_title="Distância Total (m)",
        yaxis_title="Intensidade (Metros / Minuto)"
    )
    fig.update_layout(**layout)
    return fig


def fig_ietj_vs_rsei(df: pd.DataFrame) -> go.Figure:
    """Matriz de Especificidade Neuromuscular: IETJ (%) vs RSEI (Individual P95)."""
    cols_req = ['ietj', 'rsei_individual']
    col_rsei = 'rsei_individual' if 'rsei_individual' in df.columns else 'rsei'
    
    if 'ietj' not in df.columns or col_rsei not in df.columns or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Matriz IETJ vs RSEI - Dados Ausentes</b>")
        return fig

    df_valid = df.dropna(subset=['ietj', col_rsei]).copy()
    if df_valid.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Matriz IETJ vs RSEI - Sem Registos</b>")
        return fig

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_valid['ietj'],
        y=df_valid[col_rsei],
        mode='markers+text',
        text=df_valid['player_name'],
        textposition="top center",
        marker=dict(
            size=14, 
            color=df_valid['ietj'], 
            colorscale='Magma', 
            showscale=True, 
            colorbar=dict(title="IETJ (%)")
        ),
        hovertemplate="<b>%{text}</b><br>IETJ: %{x:.1f}%<br>RSEI: %{y:.3f}<extra></extra>"
    ))

    # Linhas de referência metodológica (100% IETJ = Mediana de Jogo; 0.90 RSEI = 90% Vmáx)
    fig.add_vline(x=100.0, line_dash="dash", line_color=COLOR_GREEN, annotation_text="MD Target (100%)")
    fig.add_hline(y=0.90, line_dash="dash", line_color=COLOR_ORANGE, annotation_text="Limiar Neuromuscular (0.90)")

    layout = _layout_base()
    layout.update(
        title="<b>Matriz de Especificidade: IETJ (%) vs RSEI (P95 Vmáx)</b>",
        xaxis_title="IETJ - Especificidade Carga/Jogo (%)",
        yaxis_title="RSEI - Velocidade Relativa Individual (P95)"
    )
    fig.update_layout(**layout)
    return fig


def fig_vel_vs_acc(df: pd.DataFrame) -> go.Figure:
    """Perfil Neuromuscular: Velocidade Máxima vs Aceleração Máxima."""
    cols_req = ['top_speed_kmh', 'max_acceleration']
    if not all(c in df.columns for c in cols_req) or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Perfil Neuromuscular - Dados Ausentes</b>")
        return fig

    df_valid = df[df['top_speed_kmh'] > 0].dropna(subset=cols_req)
    if df_valid.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Perfil Neuromuscular - Sem Registos</b>")
        return fig

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_valid['max_acceleration'],
        y=df_valid['top_speed_kmh'],
        mode='markers+text',
        text=df_valid['player_name'],
        textposition="top center",
        marker=dict(size=14, color=COLOR_ORANGE, line=dict(width=1, color='white')),
        hovertemplate="<b>%{text}</b><br>Acc Máx: %{x:.2f} m/s²<br>V. Máxima: %{y:.1f} km/h<extra></extra>"
    ))

    fig.add_vline(x=df_valid['max_acceleration'].median(), line_dash="dash", line_color=TEXT_DIM)
    fig.add_hline(y=df_valid['top_speed_kmh'].median(), line_dash="dash", line_color=TEXT_DIM)

    layout = _layout_base()
    layout.update(
        title="<b>Perfil Neuromuscular: Velocidade Máxima (km/h) vs Aceleração (m/s²)</b>",
        xaxis_title="Aceleração Máxima (m/s²)",
        yaxis_title="Velocidade Máxima (km/h)"
    )
    fig.update_layout(**layout)
    return fig


def fig_acwr_longitudinal(df: pd.DataFrame, player_name: str = None) -> go.Figure:
    """Gera a curva temporal de ACWR (EWMA) com a faixa 'Sweet Spot' (0.80 - 1.30)."""
    col_acwr = next((c for c in ['acwr_ewma', 'acwr_ra', 'acwr'] if c in df.columns), None)
    if not col_acwr or 'date' not in df.columns or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Evolução Longitudinal do ACWR - Histórico Insuficiente</b>")
        return fig

    df_plot = df.copy()
    if player_name and 'player_name' in df_plot.columns:
        df_plot = df_plot[df_plot['player_name'] == player_name]

    if df_plot.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title=f"<b>Evolução do ACWR ({player_name}) - Sem Dados</b>")
        return fig

    df_agg = df_plot.groupby('date')[col_acwr].mean().reset_index().sort_values('date')

    fig = go.Figure()

    # Faixa Sweet Spot (0.80 a 1.30)
    fig.add_hrect(y0=0.80, y1=1.30, fillcolor="rgba(0, 158, 115, 0.15)", line_width=0, annotation_text="Sweet Spot (0.80 - 1.30)", annotation_position="top left")
    # Linha de Risco (> 1.50)
    fig.add_hline(y=1.50, line_dash="dash", line_color=COLOR_RED, annotation_text="Risco Elevado (> 1.50)", annotation_position="top right")

    fig.add_trace(go.Scatter(
        x=df_agg['date'],
        y=df_agg[col_acwr],
        mode='lines+markers',
        name='ACWR (EWMA)',
        line=dict(color=COLOR_SKY, width=3),
        marker=dict(size=8, color=COLOR_BLUE),
        hovertemplate="Data: %{x|%Y-%m-%d}<br>ACWR: %{y:.2f}<extra></extra>"
    ))

    layout = _layout_base()
    layout.update(
        title=f"<b>Evolução Longitudinal do ACWR (EWMA): {player_name if player_name else 'Média da Equipa'}</b>",
        xaxis_title="Data da Sessão",
        yaxis_title="Ratio Carga Aguda : Crónica",
        yaxis=dict(range=[0, max(df_agg[col_acwr].max() * 1.2, 2.0)], gridcolor=BG_LINE)
    )
    fig.update_layout(**layout)
    return fig


def fig_fases_microciclo(df: pd.DataFrame) -> go.Figure:
    """Gráfico de barras da distribuição do número de sessões por dia do microciclo."""
    if 'microcycle_day' not in df.columns or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Distribuição por Fase do Microciclo - Sem Dados</b>")
        return fig

    s = df['microcycle_day'].dropna().astype(str).str.strip()
    s = s[~s.isin(['nan', 'None', 'N/D', ''])]
    
    if s.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Distribuição por Fase - Sem Registos</b>")
        return fig

    counts = s.value_counts().reset_index()
    counts.columns = ['fase', 'n']

    fig = go.Figure(go.Bar(
        x=counts['fase'],
        y=counts['n'],
        marker_color=COLOR_BLUE,
        text=counts['n'],
        textposition='outside'
    ))

    layout = _layout_base()
    layout.update(
        title="<b>Distribuição de Sessões por Dia do Microciclo (MD)</b>",
        xaxis_title="Fase do Microciclo",
        yaxis_title="Número de Sessões / Registos"
    )
    fig.update_layout(**layout)
    return fig


def fig_foster_longitudinal(df: pd.DataFrame, player_name: str = None) -> go.Figure:
    """Gráfico de evolução de Monotonia e Strain (Foster, 1998) ao longo do tempo."""
    col_m = next((c for c in ['monotony', 'monotony_player_load'] if c in df.columns), None)
    col_s = next((c for c in ['strain', 'strain_player_load'] if c in df.columns), None)

    if not col_m or 'date' not in df.columns or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Tendência de Foster (Monotonia/Strain) - Sem Dados</b>")
        return fig

    df_plot = df.copy()
    if player_name and 'player_name' in df_plot.columns:
        df_plot = df_plot[df_plot['player_name'] == player_name]

    df_agg = df_plot.groupby('date')[[col_m] + ([col_s] if col_s else [])].mean().reset_index().sort_values('date')

    fig = go.Figure()

    # Monotonia (Eixo Principal Y1)
    fig.add_trace(go.Scatter(
        x=df_agg['date'],
        y=df_agg[col_m],
        mode='lines+markers',
        name='Monotonia',
        line=dict(color=COLOR_ORANGE, width=3),
        hovertemplate="Data: %{x|%Y-%m-%d}<br>Monotonia: %{y:.2f}<extra></extra>"
    ))

    # Limiar Alerta Monotonia (> 2.0)
    fig.add_hline(y=2.0, line_dash="dash", line_color=COLOR_RED, annotation_text="Limiar Risco (> 2.0)", annotation_position="top left")

    layout = _layout_base()
    layout.update(
        title=f"<b>Índice de Monotonia de Foster (Variabilidade de Carga): {player_name if player_name else 'Média da Equipa'}</b>",
        xaxis_title="Data da Sessão",
        yaxis_title="Monotonia (U.A.)"
    )
    fig.update_layout(**layout)
    return fig


# =============================================================================
# ABA 3: COMPARADOR DIRETO DE ATLETAS
# =============================================================================
def _extrair_metricas_comparacao(df: pd.DataFrame):
    """Mapeia dinamicamente as colunas disponíveis para os gráficos de comparação."""
    mapeamento = {
        'player_load': 'Player Load',
        'distance_m': 'Distância',
        'top_speed_kmh': 'V. Máxima',
        'distance_per_min': 'Intensidade',
        'max_acceleration': 'Acc Máx',
        'max_deceleration': 'Dec Máx'
    }
    cols = [c for c in mapeamento.keys() if c in df.columns]
    labels = [mapeamento[c] for c in cols]
    return cols, labels


def fig_radar_comparison(df: pd.DataFrame, p1: str = "A01", p2: str = "Mediana da Equipa") -> go.Figure:
    """Gráfico Radar comparativo em % do máximo do grupo."""
    cols, radar_labels = _extrair_metricas_comparacao(df)
    
    if len(cols) < 3 or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Perfil Multidimensional - Métricas Insuficientes</b>")
        return fig

    df_active = df.copy()
    if 'max_deceleration' in df_active.columns:
        df_active['max_deceleration'] = df_active['max_deceleration'].abs()

    max_vals = df_active[cols].max().replace(0, 1.0)

    # Atleta 1
    r1 = df_active[df_active['player_name'] == p1]
    val1 = r1[cols].mean() if not r1.empty else pd.Series(0, index=cols)
    lbl1 = _formatar_nome(p1)

    # Atleta 2 ou Mediana
    if p2 == "Mediana da Equipa":
        val2 = df_active[cols].median()
        lbl2 = "Mediana da Equipa"
    else:
        r2 = df_active[df_active['player_name'] == p2]
        val2 = r2[cols].mean() if not r2.empty else pd.Series(0, index=cols)
        lbl2 = _formatar_nome(p2)

    norm1 = (val1 / max_vals * 100).fillna(0).round(1).tolist()
    norm2 = (val2 / max_vals * 100).fillna(0).round(1).tolist()

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=norm1 + [norm1[0]], 
        theta=radar_labels + [radar_labels[0]],
        fill='toself', 
        name=lbl1, 
        line_color=COLOR_SKY, 
        fillcolor='rgba(86, 180, 233, 0.25)'
    ))
    fig.add_trace(go.Scatterpolar(
        r=norm2 + [norm2[0]], 
        theta=radar_labels + [radar_labels[0]],
        fill='toself', 
        name=lbl2, 
        line_color=COLOR_ORANGE, 
        fillcolor='rgba(230, 159, 0, 0.25)'
    ))

    layout = _layout_base()
    layout.update(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 110], gridcolor=BG_LINE, ticksuffix='%'),
            angularaxis=dict(gridcolor=BG_LINE, color=TEXT)
        ),
        title=f"<b>Perfil Multidimensional (% do Máximo): {lbl1} vs {lbl2}</b>"
    )
    fig.update_layout(**layout)
    return fig


def fig_normalized_bar_comparison(df: pd.DataFrame, p1: str = "A01", p2: str = "Mediana da Equipa") -> go.Figure:
    """Gráfico de barras agrupadas comparando o desvio em relação à média (100%)."""
    cols, labels = _extrair_metricas_comparacao(df)

    if not cols or df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout_base(), title="<b>Desvio Relativo - Métricas Insuficientes</b>")
        return fig

    df_active = df.copy()
    if 'max_deceleration' in df_active.columns:
        df_active['max_deceleration'] = df_active['max_deceleration'].abs()

    avg_vals = df_active[cols].mean().replace(0, 1.0)

    # Atleta 1
    r1 = df_active[df_active['player_name'] == p1]
    val1 = r1[cols].mean() if not r1.empty else pd.Series(0, index=cols)
    lbl1 = _formatar_nome(p1)

    # Atleta 2 ou Mediana
    if p2 == "Mediana da Equipa":
        val2 = df_active[cols].median()
        lbl2 = "Mediana da Equipa"
    else:
        r2 = df_active[df_active['player_name'] == p2]
        val2 = r2[cols].mean() if not r2.empty else pd.Series(0, index=cols)
        lbl2 = _formatar_nome(p2)

    pct1 = (val1 / avg_vals * 100).fillna(0).round(1)
    pct2 = (val2 / avg_vals * 100).fillna(0).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=lbl1, 
        x=labels, 
        y=pct1.values, 
        marker_color=COLOR_SKY,
        text=[f"{v:.1f}%" for v in pct1.values], 
        textposition='outside'
    ))
    fig.add_trace(go.Bar(
        name=lbl2, 
        x=labels, 
        y=pct2.values, 
        marker_color=COLOR_ORANGE,
        text=[f"{v:.1f}%" for v in pct2.values], 
        textposition='outside'
    ))

    fig.add_hline(y=100, line_dash="dash", line_color=COLOR_RED, annotation_text="Média da Equipa (100%)")
    max_y = max(pct1.max() if not pct1.empty else 100, pct2.max() if not pct2.empty else 100, 120) * 1.15

    layout = _layout_base()
    layout.update(
        barmode='group',
        title=f"<b>Desvio Relativo em Relação à Média (100%): {lbl1} vs {lbl2}</b>",
        yaxis_title="% em Relação à Média da Equipa",
        yaxis=dict(range=[0, max_y], gridcolor=BG_LINE, ticksuffix="%")
    )
    fig.update_layout(**layout)
    return fig