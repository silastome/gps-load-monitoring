"""
===============================================================================
UTILITÁRIO DE DIAGNÓSTICO DE REPOSITÓRIO (DIAGNOSTICO_REPO.PY)
===============================================================================
Descrição: Percorre a árvore do projeto, inspeciona cabeçalhos/amostras de CSVs
           e extrai a estrutura de funções e classes dos scripts Python,
           gerando um relatório consolidador em 'relatorio_diagnostico.txt'.
===============================================================================
"""

import csv
import json
import os
from pathlib import Path


def gerar_diagnostico(diretorio_alvo: str = ".", ficheiro_saida: str = "relatorio_diagnostico.txt"):
    root = Path(diretorio_alvo).resolve()
    linhas_out = []
    script_atual = Path(__file__).name

    def log(texto: str = ""):
        linhas_out.append(str(texto))

    log("=" * 80)
    log(f"DIAGNÓSTICO COMPLETO DO REPOSITÓRIO: {root.name}")
    log(f"Caminho Absoluto: {root}")
    log("=" * 80)

    # 1. ESTRUTURA DE PASTAS E FICHEIROS
    log("\n1. ESTRUTURA DE FICHEIROS E PASTAS")
    log("-" * 60)
    ignore_dirs = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".idea",
        ".vscode",
        "cache",
    }

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        rel_path = Path(current_root).relative_to(root)
        depth = len(rel_path.parts) if str(rel_path) != "." else 0
        indent = "  " * depth
        folder_name = rel_path.name if str(rel_path) != "." else root.name
        log(f"{indent}📁 {folder_name}/")

        subindent = "  " * (depth + 1)
        for f in files:
            if not f.startswith("."):
                log(f"{subindent}📄 {f}")

    # 2. ANÁLISE DE CABEÇALHOS E AMOSTRAS DE CSVs
    log("\n2. CABEÇALHOS E AMOSTRAS DE FICHEIROS CSV")
    log("-" * 60)
    csv_files = [
        p for p in root.glob("**/*.csv")
        if not any(idr in p.parts for idr in ignore_dirs)
    ]

    if not csv_files:
        log("Nenhum ficheiro CSV encontrado.")
    else:
        for csv_path in csv_files[:10]:
            rel = csv_path.relative_to(root)
            log(f"\n--- CSV: {rel} ---")
            try:
                with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f_csv:
                    reader = csv.reader(f_csv)
                    header = next(reader, None)
                    log(f"Colunas ({len(header) if header else 0}): {header}")
                    log("Amostra das 3 primeiras linhas de dados:")
                    for i, row in enumerate(reader):
                        if i >= 3:
                            break
                        log(f"  Linha {i+1}: {row}")
            except Exception as e:
                log(f"Erro ao ler {rel}: {e}")

    # 3. EXTRAÇÃO DE ESTRUTURA DOS SCRIPTS PYTHON
    log("\n3. ESTRUTURA DE SCRIPTS PYTHON (.py)")
    log("-" * 60)
    py_files = [
        p for p in root.glob("**/*.py")
        if not any(idr in p.parts for idr in ignore_dirs)
        and p.name != Path(ficheiro_saida).name
        and p.name != script_atual
    ]

    for py_path in py_files:
        rel = py_path.relative_to(root)
        log(f"\n--- Python: {rel} ---")
        try:
            with open(py_path, "r", encoding="utf-8", errors="replace") as f_py:
                content = f_py.read()
                lines = content.splitlines()
                log(f"Total de linhas: {len(lines)}")

                defs = [
                    l.strip()
                    for l in lines
                    if l.strip().startswith((
                        "def ",
                        "class ",
                        "MAPA",
                        "T =",
                        "CONFIG",
                        "COLUNAS",
                        "BASE_DIR",
                    ))
                ]
                if defs:
                    log("Principais Definições / Variáveis / Funções:")
                    for d in defs[:30]:
                        log(f"  {d}")
                else:
                    log("Primeiras 15 linhas:")
                    for l in lines[:15]:
                        log(f"  {l}")
        except Exception as e:
            log(f"Erro ao ler {rel}: {e}")

    caminho_out = root / ficheiro_saida
    with open(caminho_out, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(linhas_out))

    print(f"✅ Diagnóstico concluído!")
    print(f"📄 Ficheiro gerado com sucesso em: {caminho_out}")


if __name__ == "__main__":
    gerar_diagnostico()