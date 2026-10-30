def obter_ou_criar_sessao(cursor, data_sessao, tipo_sessao="Treino Principal"):
    cursor.execute("SELECT id FROM sessoes WHERE data = ? AND tipo = ?", (data_sessao, tipo_sessao))
    res = cursor.fetchone()
    if res:
        return res["id"]
    
    cursor.execute("INSERT INTO sessoes (data, tipo) VALUES (?, ?)", (data_sessao, tipo_sessao))
    return cursor.lastrowid
