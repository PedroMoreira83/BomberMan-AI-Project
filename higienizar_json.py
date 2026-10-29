import json

with open("q_table_j1.json", "r", encoding="utf-8") as f:
    dados = json.load(f)

tabela = dados.get("q_table", dados)
nova_tabela = {}

for estado, acoes in tabela.items():
    # Analisa o contexto da chave de estado
    partes = {k: v for k, v in [token.split(":", 1) for token in estado.split("_") if ":" in token]}
    sem_tijolo = "1" not in (partes.get("C"), partes.get("B"), partes.get("E"), partes.get("D"))
    
    acoes_limpas = {}
    for acao, valor in acoes.items():
        novo_valor = valor
        # Derruba bombas milionárias injustificadas
        if acao == "bomba" and sem_tijolo and partes.get("Dist") != "Perto":
            novo_valor = min(valor, -40.0)
        # Reduz pela metade a inflação absurda nos outros movimentos
        elif valor > 300:
            novo_valor = 300 + ((valor - 300) * 0.5)
            
        acoes_limpas[acao] = round(novo_valor, 2)
    nova_tabela[estado] = acoes_limpas

dados["q_table"] = nova_tabela

with open("q_table_j1.json", "w", encoding="utf-8") as f:
    json.dump(dados, f)
print("Limpeza concluída! A tabela foi desinflada.")