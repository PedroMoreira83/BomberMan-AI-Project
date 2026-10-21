import random
import json
import os

ALFA = 0.1      
GAMA = 0.95           # Aumentei para 0.95 para ela dar mais valor ao futuro (sobrevivência)
EPSILON = 1.0         
EPSILON_MIN = 0.05    
EPSILON_DECAY = 0.9995 # Acelerei um pouco o decaimento para ela parar de ser aleatória mais cedo

ACOES = ["cima", "baixo", "esquerda", "direita", "bomba", "parado"]
ARQUIVO_MEMORIA = "q_table_j1.json" 

q_table = {}
estado_anterior = None
acao_anterior = None
passos = 0 

if os.path.exists(ARQUIVO_MEMORIA):
    with open(ARQUIVO_MEMORIA, "r") as f:
        q_table = json.load(f)

def obter_estado_simplificado(self_state, mapa, bombas, jogadores):
    x = self_state['grid_x']
    y = self_state['grid_y']
    
    def ver_celula(nx, ny):
        if 0 <= nx < 13 and 0 <= ny < 11:
            return mapa[ny][nx]
        return 2  
    
    acima = ver_celula(x, y - 1)
    abaixo = ver_celula(x, y + 1)
    esquerda = ver_celula(x - 1, y)
    direita = ver_celula(x + 1, y)
    
    em_perigo = "N"
    rota_fuga = "NA"
    
    # 1. VERIFICAÇÃO DE PERIGO
    for b in bombas:
        if not b.explodida:
            if b.x == x or b.y == y:
                alcance = 1 + (b.nivel - 1) * 2
                distancia = abs(b.x - x) + abs(b.y - y)
                if distancia <= alcance:
                    em_perigo = "S"
                    break

    # 2. NOVO: GPS DE FUGA (Se estiver em perigo, para onde correr?)
    if em_perigo == "S":
        direcoes_adj = {"C": (x, y - 1), "B": (x, y + 1), "E": (x - 1, y), "D": (x + 1, y)}
        fugas = []
        
        for d_nome, (nx, ny) in direcoes_adj.items():
            # Se o bloco ao lado for caminhável (vazio ou powerup)
            if 0 <= nx < 13 and 0 <= ny < 11 and mapa[ny][nx] in [0, 3, 4]:
                vizinho_seguro = True
                # Confirma se esse bloco não está na reta de outra bomba
                for b in bombas:
                    if not b.explodida:
                        if b.x == nx or b.y == ny:
                            alcance = 1 + (b.nivel - 1) * 2
                            if (abs(b.x - nx) + abs(b.y - ny)) <= alcance:
                                vizinho_seguro = False
                                break
                if vizinho_seguro:
                    fugas.append(d_nome)
        
        # Se achou uma saída, aponta a primeira. Se não, declara beco sem saída.
        if fugas:
            rota_fuga = fugas[0]
        else:
            rota_fuga = "Nenhuma"

    # 3. RADAR DE INIMIGOS
    menor_distancia = 999
    dir_x, dir_y = "Igual", "Igual"
    dist_inimigo = "Longe"
    
    for p in jogadores:
        if p.ativo and (p.grid_x != x or p.grid_y != y):
            dist = abs(p.grid_x - x) + abs(p.grid_y - y)
            if dist < menor_distancia:
                menor_distancia = dist
                dir_x = "D" if p.grid_x > x else "E" if p.grid_x < x else "Igual"
                dir_y = "B" if p.grid_y > y else "C" if p.grid_y < y else "Igual"

    if menor_distancia <= 3:
        dist_inimigo = "Perto"
    elif menor_distancia <= 6:
        dist_inimigo = "Medio"

    bombas_ativas = self_state['bombas_ativas']
    
    # Adicionamos a Fuga ao estado mental dela
    return f"C:{acima}_B:{abaixo}_E:{esquerda}_D:{direita}_Perigo:{em_perigo}_Fuga:{rota_fuga}_AlvoX:{dir_x}_AlvoY:{dir_y}_Dist:{dist_inimigo}"

def calcular_recompensa(estado_ant, acao_ant, estado_atual, self_state, mapa, jogadores):
    recompensa = -1  
    
    if not self_state['ativo']:
        return -1000

    if acao_ant in ["cima", "baixo", "esquerda", "direita"] and estado_ant == estado_atual:
        recompensa -= 10
        
    # Punição por criar um beco sem saída
    if "Perigo:S" in estado_atual and "Fuga:Nenhuma" in estado_atual:
        recompensa -= 200

    if "Perigo:S" in estado_atual:
        recompensa -= 30  
    if "Perigo:S" in estado_ant and "Perigo:N" in estado_atual:
        recompensa += 200 

    # --- NOVO: RECOMPENSA POR OBEDECER O GPS DE FUGA ---
    # Se ela estava em perigo no frame anterior e obedeceu a direção do GPS
    if "Perigo:S" in estado_ant and "Fuga:NA" not in estado_ant and "Fuga:Nenhuma" not in estado_ant:
        direcao_fuga = estado_ant.split("Fuga:")[1].split("_")[0]
        mapa_fugas = {"C": "cima", "B": "baixo", "E": "esquerda", "D": "direita"}
        if mapa_fugas.get(direcao_fuga) == acao_ant:
            recompensa += 100  # Ela ganha pontos instantâneos apenas por iniciar a fuga corretamente!

    elif acao_ant == "parado":
        if "Perigo:S" in estado_atual:
            recompensa -= 30 

    elif acao_ant in ["cima", "baixo", "esquerda", "direita"]:
        if "Dist:Longe" in estado_ant and "Dist:Medio" in estado_atual:
            recompensa += 30  
        elif "Dist:Medio" in estado_ant and "Dist:Perto" in estado_atual:
            recompensa += 50  
        elif ("Dist:Perto" in estado_ant and "Dist:Medio" in estado_atual) and "Perigo:N" in estado_atual:
            recompensa -= 15

    elif acao_ant == "bomba":
        if "Perigo:S" in estado_ant:
            recompensa -= 500
        elif "Dist:Perto" in estado_ant:
            recompensa += 300
        else:
            x = self_state['grid_x']
            y = self_state['grid_y']
            alvos_atingidos = 0
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < 13 and 0 <= ny < 11 and mapa[ny][nx] == 1:
                    alvos_atingidos += 1
                    
            if alvos_atingidos > 0:
                recompensa += (50 * alvos_atingidos)  
            else:
                recompensa -= 100  
            
    return recompensa

def decidir_acao(player, mapa, jogadores, bombas, tempo_restante, pontos, hud_info, self_state):
    global q_table, estado_anterior, acao_anterior, EPSILON, passos
    
    estado_atual = obter_estado_simplificado(self_state, mapa, bombas, jogadores)
    
    if estado_atual not in q_table:
        q_table[estado_atual] = {acao: 0.0 for acao in ACOES}
        
    if estado_anterior is not None and acao_anterior is not None:
        recompensa = calcular_recompensa(estado_anterior, acao_anterior, estado_atual, self_state, mapa, jogadores)
        q_antigo = q_table[estado_anterior][acao_anterior]
        max_q_futuro = max(q_table[estado_atual].values())
        q_table[estado_anterior][acao_anterior] = q_antigo + ALFA * (recompensa + GAMA * max_q_futuro - q_antigo)

    if random.uniform(0, 1) < EPSILON:
        acao_escolhida = random.choice(ACOES)
    else:
        acao_escolhida = max(q_table[estado_atual], key=q_table[estado_atual].get)

    if EPSILON > EPSILON_MIN:
        EPSILON *= EPSILON_DECAY

    estado_anterior = estado_atual
    acao_anterior = acao_escolhida

    passos += 1
    if passos % 100 == 0:
        with open(ARQUIVO_MEMORIA, "w") as f:
            json.dump(q_table, f)

    return acao_escolhida