def obter_ou_criar_jogador(cursor, nome_atleta_real):
    cursor.execute("SELECT id, nome FROM jogadores WHERE nome_real = ?", (nome_atleta_real,))
    res = cursor.fetchone()
    if res:
        return res["id"], res["nome"]
    
    cursor.execute("SELECT COUNT(*) as total FROM jogadores")
    total = cursor.fetchone()["total"] + 1
    nome_anonimo = "Atleta {:02d}".format(total)
    
    cursor.execute(
        "INSERT INTO jogadores (nome, nome_real) VALUES (?, ?)",
        (nome_anonimo, nome_atleta_real)
    )
    return cursor.lastrowid, nome_anonimo

def listar_jogadores(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, posicao FROM jogadores ORDER BY id ASC")
    return cursor.fetchall()
