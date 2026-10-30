import os
import json
import pandas as pd

df = pd.read_csv('dados_base.csv')
df['date'] = pd.to_datetime(df['date'])

os.makedirs('outputs', exist_ok=True)
os.makedirs('cache', exist_ok=True)

df.to_csv('outputs/conversao_dash_final.csv', index=False)
df.to_csv('cache/player_master_v3.csv.gz', index=False, compression='gzip')
df.to_csv('cache/clusters_sessoes.csv', index=False)

if 'ietj' in df.columns:
    ietj_fase = df.groupby('microcycle_day')['ietj'].agg(['median', 'mean', 'count']).reset_index()
    ietj_fase.to_csv('outputs/ietj_por_fase.csv', index=False)

    bins = [-1, 25, 50, 75, 100, 999]
    labels = ['<25% (Muito Baixa)', '25-50% (Baixa)', '50-75% (Moderada)', '75-100% (Elevada)', '>100% (Maxima)']
    df['ietj_faixa'] = pd.cut(df['ietj'], bins=bins, labels=labels)
    faixas = df['ietj_faixa'].value_counts().reset_index()
    faixas.columns = ['faixa', 'count']
    faixas.to_csv('outputs/ietj_faixas.csv', index=False)

qc = {
    "registos_finais": int(len(df)),
    "atletas_incluidos": int(df['player_name'].nunique()),
    "dias_monitorizados": int(df['date'].dt.date.nunique())
}
with open('cache/qc_report.json', 'w') as f:
    json.dump(qc, f, indent=2)

print("Dados preparados em outputs/ e cache/.")
