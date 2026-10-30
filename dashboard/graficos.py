import numpy as np
import pandas as pd
import plotly.graph_objects as go

BG_PANEL = "#1e293b"
BG_LINE = "#334155"
TEXT = "#e2e8f0"


def _layout_base():
    return dict(
        paper_bgcolor=BG_PANEL,
        plot_bgcolor=BG_PANEL,
        font=dict(color=TEXT, family="Segoe UI, sans-serif"),
        margin=dict(l=70, r=80, t=50, b=40),
        xaxis=dict(gridcolor=BG_LINE, zerolinecolor=BG_LINE),
        yaxis=dict(gridcolor=BG_LINE, zerolinecolor=BG_LINE),
    )


# --- ABA 1: SESSÃO GPS ---
def fig_ranking_bar(df, col, title, x_label, unit="", color="#0072B2"):
    df_valid = df[df[col] > 0].dropna(subset=[col]).sort_values(col, ascending=True)
    if df_valid.empty:
        fig = go.Figure()
        layout = _layout_base()
        layout.update(title=f"<b>{title} - Sem Dados</b>")
        fig.update_layout(**layout)
        return fig

    colors = [color] * len(df_valid)
    if len(colors) >= 2:
        colors[-1] = '#f59e0b'
        colors[0] = '#64748b'

    text_labels = [f"{val:.1f} {unit}".strip() if isinstance(val, float) and val % 1 != 0 else f"{int(val)} {unit}".strip() for val in df_valid[col]]

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
    fig.add_vline(x=media, line_dash="dash", line_color="#ef4444", annotation_text=f"Média: {media:.1f}{unit}", annotation_position="top right")

    max_x = df_valid[col].max() * 1.22
    layout = _layout_base()
    layout.update(
        title=f"<b>{title}</b>",
        xaxis_title=x_label,
        xaxis=dict(range=[0, max_x], gridcolor=BG_LINE),
        yaxis=dict(gridcolor=BG_LINE)
    )
    fig.update_layout(**layout)
    return fig


def fig_perfil_mecanico(df):
    df_valid = df[df['distance_m'] > 0].dropna(subset=['max_acceleration', 'max_deceleration']).copy()
    if df_valid.empty:
        fig = go.Figure()
        layout = _layout_base()
        layout.update(title="<b>Perfil Mecânico (Aceleração vs Desaceleração)</b>")
        fig.update_layout(**layout)
        return fig

    df_valid['max_deceleration'] = df_valid['max_deceleration'].abs()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_valid['max_acceleration'],
        y=df_valid['max_deceleration'],
        mode='markers+text',
        text=df_valid['player_name'],
        textposition="top center",
        marker=dict(size=13, color='#38bdf8', line=dict(width=1, color='white')),
        hovertemplate="<b>Atleta %{text}</b><br>Acc Máx: %{x:.2f} m/s²<br>Dec Máx: %{y:.2f} m/s²<extra></extra>"
    ))

    med_x = df_valid['max_acceleration'].median()
    med_y = df_valid['max_deceleration'].median()
    fig.add_vline(x=med_x, line_dash="dash", line_color="#94a3b8")
    fig.add_hline(y=med_y, line_dash="dash", line_color="#94a3b8")

    layout = _layout_base()
    layout.update(
        title="<b>Perfil Mecânico: Aceleração vs Desaceleração Máxima (m/s²)</b>",
        xaxis_title="Aceleração Máxima (m/s²)",
        yaxis_title="Desaceleração Máxima (m/s²)"
    )
    fig.update_layout(**layout)
    return fig


# --- ABA 2: MATRIZ & PERFIS DA CARGA ---
def fig_quadrantes_volume_intensidade(df):
    df_valid = df[df['distance_m'] > 0].dropna(subset=['distance_m', 'distance_per_min'])
    if df_valid.empty:
        fig = go.Figure()
        layout = _layout_base()
        layout.update(title="<b>Matriz Locomotora (Volume vs Intensidade)</b>")
        fig.update_layout(**layout)
        return fig

    med_dist = df_valid['distance_m'].median()
    med_int = df_valid['distance_per_min'].median()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_valid['distance_m'],
        y=df_valid['distance_per_min'],
        mode='markers+text',
        text=df_valid['player_name'],
        textposition="top center",
        marker=dict(size=14, color=df_valid['player_load'], colorscale='Viridis', showscale=True, colorbar=dict(title="Player Load")),
        hovertemplate="<b>Atleta %{text}</b><br>Distância: %{x:.0f} m<br>Intensidade: %{y:.1f} m/min<extra></extra>"
    ))

    fig.add_vline(x=med_dist, line_dash="dash", line_color="#94a3b8")
    fig.add_hline(y=med_int, line_dash="dash", line_color="#94a3b8")

    layout = _layout_base()
    layout.update(
        title="<b>Matriz Locomotora: Volume (Distância) vs Intensidade (m/min)</b>",
        xaxis_title="Distância Total (m)",
        yaxis_title="Intensidade (Metros / Minuto)"
    )
    fig.update_layout(**layout)
    return fig


def fig_vel_vs_acc(df):
    df_valid = df[df['top_speed_kmh'] > 0].dropna(subset=['top_speed_kmh', 'max_acceleration'])
    if df_valid.empty:
        fig = go.Figure()
        layout = _layout_base()
        layout.update(title="<b>Perfil Neuromuscular (Velocidade vs Aceleração)</b>")
        fig.update_layout(**layout)
        return fig

    med_v = df_valid['top_speed_kmh'].median()
    med_a = df_valid['max_acceleration'].median()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_valid['max_acceleration'],
        y=df_valid['top_speed_kmh'],
        mode='markers+text',
        text=df_valid['player_name'],
        textposition="top center",
        marker=dict(size=14, color='#f59e0b', line=dict(width=1, color='white')),
        hovertemplate="<b>Atleta %{text}</b><br>Acc Máx: %{x:.2f} m/s²<br>V. Máxima: %{y:.1f} km/h<extra></extra>"
    ))

    fig.add_vline(x=med_a, line_dash="dash", line_color="#94a3b8")
    fig.add_hline(y=med_v, line_dash="dash", line_color="#94a3b8")

    layout = _layout_base()
    layout.update(
        title="<b>Perfil Neuromuscular: Velocidade Máxima (km/h) vs Aceleração (m/s²)</b>",
        xaxis_title="Aceleração Máxima (m/s²)",
        yaxis_title="Velocidade Máxima (km/h)"
    )
    fig.update_layout(**layout)
    return fig


# --- ABA 3: COMPARADOR DIRETO DE ATLETAS ---
def fig_radar_comparison(df, p1="A01", p2="A02"):
    cols = ['player_load', 'distance_m', 'top_speed_kmh', 'distance_per_min', 'max_acceleration', 'max_deceleration']
    radar_labels = ['Player Load', 'Distância', 'V. Máxima', 'Intensidade', 'Acc Máx', 'Dec Máx']

    df_active = df[df['distance_m'] > 0]
    max_vals = df_active[cols].max().replace(0, 1)

    r1 = df[df['player_name'] == p1]
    val1 = r1[cols].iloc[0] if not r1.empty else pd.Series(0, index=cols)

    if p2 == "Mediana da Equipa":
        val2 = df_active[cols].median()
        label2 = "Mediana da Equipa"
    else:
        r2 = df[df['player_name'] == p2]
        val2 = r2[cols].iloc[0] if not r2.empty else pd.Series(0, index=cols)
        label2 = f"Atleta {p2}"

    norm1 = (val1 / max_vals * 100).round(1).tolist()
    norm2 = (val2 / max_vals * 100).round(1).tolist()

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=norm1 + [norm1[0]], theta=radar_labels + [radar_labels[0]],
        fill='toself', name=f"Atleta {p1}", line_color='#38bdf8', fillcolor='rgba(56, 189, 248, 0.25)'
    ))
    fig.add_trace(go.Scatterpolar(
        r=norm2 + [norm2[0]], theta=radar_labels + [radar_labels[0]],
        fill='toself', name=label2, line_color='#f59e0b', fillcolor='rgba(245, 158, 11, 0.25)'
    ))

    layout = _layout_base()
    layout.update(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 110], gridcolor=BG_LINE, ticksuffix='%'),
            angularaxis=dict(gridcolor=BG_LINE, color=TEXT)
        ),
        title=f"<b>Perfil Multidimensional (% do Máximo): Atleta {p1} vs {label2}</b>"
    )
    fig.update_layout(**layout)
    return fig


def fig_normalized_bar_comparison(df, p1="A01", p2="A02"):
    cols = ['player_load', 'distance_m', 'top_speed_kmh', 'distance_per_min', 'max_acceleration', 'max_deceleration']
    labels = ['Player Load', 'Distância', 'V. Máxima', 'Intensidade', 'Acc Máx', 'Dec Máx']

    df_active = df[df['distance_m'] > 0]
    avg_vals = df_active[cols].mean().replace(0, 1)

    r1 = df[df['player_name'] == p1]
    val1 = r1[cols].iloc[0] if not r1.empty else pd.Series(0, index=cols)

    if p2 == "Mediana da Equipa":
        val2 = df_active[cols].median()
        label2 = "Mediana da Equipa"
    else:
        r2 = df[df['player_name'] == p2]
        val2 = r2[cols].iloc[0] if not r2.empty else pd.Series(0, index=cols)
        label2 = f"Atleta {p2}"

    pct1 = (val1 / avg_vals * 100).round(1)
    pct2 = (val2 / avg_vals * 100).round(1)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=f"Atleta {p1}", x=labels, y=pct1.values, marker_color='#38bdf8',
        text=[f"{v:.1f}%" for v in pct1.values], textposition='outside'
    ))
    fig.add_trace(go.Bar(
        name=label2, x=labels, y=pct2.values, marker_color='#f59e0b',
        text=[f"{v:.1f}%" for v in pct2.values], textposition='outside'
    ))

    fig.add_hline(y=100, line_dash="dash", line_color="#ef4444", annotation_text="Média da Equipa (100%)")
    max_y = max(pct1.max(), pct2.max(), 120) * 1.15

    layout = _layout_base()
    layout.update(
        barmode='group',
        title=f"<b>Desvio Relativo em Relação à Média (100%): Atleta {p1} vs {label2}</b>",
        yaxis_title="% em Relação à Média da Equipa",
        yaxis=dict(range=[0, max_y], gridcolor=BG_LINE, ticksuffix="%")
    )
    fig.update_layout(**layout)
    return fig
