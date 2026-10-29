import glob
import json
import os
import importlib

ARQUIVO_MESTRE_PY = "memoria_mestre.py"

SEMENTES_GEN14 = {
    "C:2_B:0_E:2_D:0_Perigo:N_Fuga:NA_AlvoX:Igual_AlvoY:B_Dist:Longe": {"cima": -15.0, "baixo": 1142.83, "esquerda": -15.0, "direita": 494.86, "bomba": -50.0, "parado": -10.0},
    "C:0_B:1_E:2_D:2_Perigo:N_Fuga:NA_AlvoX:D_AlvoY:B_Dist:Longe": {"cima": 869.62, "baixo": -15.0, "esquerda": -15.0, "direita": -15.0, "bomba": 1113.89, "parado": -10.0},
}

def decompor_estado(estado_str):
    partes = {}
    for token in estado_str.split("_"):
        if ":" in token:
            k, v = token.split(":", 1)
            partes[k] = v
    return partes

def montar_estado(p):
    return f"C:{p['C']}_B:{p['B']}_E:{p['E']}_D:{p['D']}_Perigo:{p['Perigo']}_Fuga:{p['Fuga']}_AlvoX:{p['AlvoX']}_AlvoY:{p['AlvoY']}_Dist:{p['Dist']}"

def higienizar_acoes_fisicas(estado_str, acoes_dict):
    p = decompor_estado(estado_str)
    limpas = {k: float(v) for k, v in acoes_dict.items()}

    mapa_colisao = [("C", "cima"), ("B", "baixo"), ("E", "esquerda"), ("D", "direita")]
    for chave_dir, nome_acao in mapa_colisao:
        if p.get(chave_dir) in ("1", "2") and limpas.get(nome_acao, 0.0) > -5.0:
            limpas[nome_acao] = -15.0

    if p.get("Perigo") == "N" and limpas.get("parado", 0.0) > 0.0:
        limpas["parado"] = -10.0

    # Profilaxia: Derruba o valor da bomba para -40 se não houver tijolo vizinho nem inimigo perto
    sem_tijolo = "1" not in (p.get("C"), p.get("B"), p.get("E"), p.get("D"))
    if sem_tijolo and p.get("Dist") != "Perto":
        if limpas.get("bomba", 0.0) > -40.0:
            limpas["bomba"] = -40.0

    return limpas

def gerar_8_simetrias_diedrais(estado_str, acoes_dict):
    p_base = decompor_estado(estado_str)
    chaves_obrigatorias = {"C", "B", "E", "D", "Perigo", "Fuga", "AlvoX", "AlvoY", "Dist"}
    if not chaves_obrigatorias.issubset(p_base.keys()): return [(estado_str, acoes_dict)]

    acoes_limpas = higienizar_acoes_fisicas(estado_str, acoes_dict)
    reflexoes_4 = []

    for flip_x in (False, True):
        for flip_y in (False, True):
            p, a = p_base.copy(), acoes_limpas.copy()
            if flip_x:
                p["E"], p["D"] = p["D"], p["E"]
                if p["Fuga"] in ("E", "D"): p["Fuga"] = "D" if p["Fuga"] == "E" else "E"
                if p["AlvoX"] in ("E", "D"): p["AlvoX"] = "D" if p["AlvoX"] == "E" else "E"
                a["esquerda"], a["direita"] = a["direita"], a["esquerda"]
            if flip_y:
                p["C"], p["B"] = p["B"], p["C"]
                if p["Fuga"] in ("C", "B"): p["Fuga"] = "B" if p["Fuga"] == "C" else "C"
                if p["AlvoY"] in ("C", "B"): p["AlvoY"] = "B" if p["AlvoY"] == "C" else "C"
                a["cima"], a["baixo"] = a["baixo"], a["cima"]
            reflexoes_4.append((montar_estado(p), a))

    todas_8 = list(reflexoes_4)
    mapa_fuga_t = {"C": "E", "E": "C", "B": "D", "D": "B", "Nenhuma": "Nenhuma", "NA": "NA"}
    mapa_xy, mapa_yx = {"E": "C", "D": "B", "Igual": "Igual"}, {"C": "E", "B": "D", "Igual": "Igual"}

    for s4, a4 in reflexoes_4:
        p4 = decompor_estado(s4)
        pt, at = p4.copy(), a4.copy()
        pt["C"], pt["E"] = p4["E"], p4["C"]
        pt["B"], pt["D"] = p4["D"], p4["B"]
        pt["Fuga"] = mapa_fuga_t.get(p4["Fuga"], p4["Fuga"])
        pt["AlvoX"], pt["AlvoY"] = mapa_yx.get(p4["AlvoY"], p4["AlvoY"]), mapa_xy.get(p4["AlvoX"], p4["AlvoX"])
        at["cima"], at["esquerda"] = a4["esquerda"], a4["cima"]
        at["baixo"], at["direita"] = a4["direita"], a4["baixo"]
        todas_8.append((montar_estado(pt), at))

    return todas_8

def mesclar_estado(memoria_destino, estado, acoes_novas, peso_novo=0.25):
    if estado not in memoria_destino:
        memoria_destino[estado] = {k: round(float(v), 2) for k, v in acoes_novas.items()}
        return

    atuais = memoria_destino[estado]
    for acao, val_novo in acoes_novas.items():
        val_novo = float(val_novo)
        val_atual = float(atuais.get(acao, 0.0))
        # Substitui a lógica de catraca (apenas se maior) pela média ponderada
        atuais[acao] = round(((1.0 - peso_novo) * val_atual) + (peso_novo * val_novo), 2)

def aglutinar_todos_arquivos(padrao_json="*.json"):
    memoria_consolidada = {}
    if os.path.exists(ARQUIVO_MESTRE_PY):
        try:
            import memoria_mestre
            importlib.reload(memoria_mestre)
            for s, acts in getattr(memoria_mestre, "MEMORIA_MESTRE", {}).items():
                memoria_consolidada[s] = higienizar_acoes_fisicas(s, acts)
        except Exception: pass

    for estado_sem, acoes_sem in SEMENTES_GEN14.items():
        for est_sim, acoes_sim in gerar_8_simetrias_diedrais(estado_sem, acoes_sem):
            mesclar_estado(memoria_consolidada, est_sim, acoes_sim, peso_novo=0.5)

    for caminho_json in sorted(glob.glob(padrao_json)):
        try:
            with open(caminho_json, "r", encoding="utf-8") as f:
                dados = json.load(f)
            tabela = dados.get("q_table", dados)
            if not isinstance(tabela, dict): continue
            for estado, acoes in tabela.items():
                if not isinstance(acoes, dict): continue
                for est_sim, acoes_sim in gerar_8_simetrias_diedrais(estado, acoes):
                    mesclar_estado(memoria_consolidada, est_sim, acoes_sim)
        except Exception: pass

    with open(ARQUIVO_MESTRE_PY, "w", encoding="utf-8") as f:
        f.write("# ARQUIVO GERADO AUTOMATICAMENTE PELO AGLUTINADOR DE MEMORIA\n")
        f.write(f"# Total de estados consolidados e espelhados (D4): {len(memoria_consolidada)}\n\n")
        f.write("MEMORIA_MESTRE = {\n")
        for est, acts in sorted(memoria_consolidada.items()):
            f.write(f"    {repr(est)}: {repr(acts)},\n")
        f.write("}\n")
    return memoria_consolidada

if __name__ == "__main__":
    mem = aglutinar_todos_arquivos()
    print(f"[OK] {ARQUIVO_MESTRE_PY} gerado com {len(mem)} estados!")