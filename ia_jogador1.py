import random
import json
import os

ALFA = 0.1      
GAMA = 0.95           
EPSILON = 1.0         
EPSILON_MIN = 0.05    
EPSILON_DECAY = 0.9995 

ACOES = ["cima", "baixo", "esquerda", "direita", "bomba", "parado"]
ARQUIVO_MEMORIA = "q_table_j1.json" 

q_table = {}
estado_anterior = None
acao_anterior = None
passos = 0 

# --- CARREGAMENTO PERSISTENTE DO EPSILON ---
if os.path.exists(ARQUIVO_MEMORIA):
    with open(ARQUIVO_MEMORIA, "r") as f:
        dados = json.load(f)
        if "metadata" in dados:
            q_table = dados["q_table"]
            EPSILON = dados["metadata"].get("epsilon", EPSILON)
        else:
            q_table = dados

def resetar_episodio(morreu=False):
    global estado_anterior, acao_anterior, q_table, EPSILON
    
    if morreu and estado_anterior is not None and acao_anterior is not None:
        q_antigo = q_table[estado_anterior][acao_anterior]
        # Aplica a punição terminal fatal de -1000 pela morte corrigida
        q_table[estado_anterior][acao_anterior] = q_antigo + ALFA * (-1000 - q_antigo)
        
        with open(ARQUIVO_MEMORIA, "w") as f:
            json.dump({"metadata": {"epsilon": EPSILON}, "q_table": q_table}, f)

    estado_anterior = None
    acao_anterior = None

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
    
    # 1. VERIFICAÇÃO DE PERIGO COM RAYCASTING 
    for b in bombas:
        if not b.explodida:
            alcance = 1 + (b.nivel - 1) * 2
            if b.x == x and b.y == y:
                em_perigo = "S"
                break
            
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                for i in range(1, alcance + 1):
                    nx, ny = b.x + dx * i, b.y + dy * i
                    if not (0 <= nx < 13 and 0 <= ny < 11): break
                    celula = ver_celula(nx, ny)
                    if celula == 2: break 
                    if nx == x and ny == y:
                        em_perigo = "S"
                        break
                    if celula == 1: break 
                if em_perigo == "S": break
        if em_perigo == "S": break

    # 2. GPS DE FUGA COM RAYCASTING 
    if em_perigo == "S":
        direcoes_adj = {"C": (x, y - 1), "B": (x, y + 1), "E": (x - 1, y), "D": (x + 1, y)}
        fugas = []
        
        for d_nome, (nx, ny) in direcoes_adj.items():
            if 0 <= nx < 13 and 0 <= ny < 11 and mapa[ny][nx] in [0, 3, 4]:
                vizinho_seguro = True
                
                for b in bombas:
                    if not b.explodida:
                        alcance = 1 + (b.nivel - 1) * 2
                        if b.x == nx and b.y == ny:
                            vizinho_seguro = False
                            break
                            
                        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                            for i in range(1, alcance + 1):
                                bx, by = b.x + dx * i, b.y + dy * i
                                if not (0 <= bx < 13 and 0 <= by < 11): break
                                celula_b = ver_celula(bx, by)
                                if celula_b == 2: break 
                                if bx == nx and by == ny:
                                    vizinho_seguro = False
                                    break
                                if celula_b == 1: break 
                        if not vizinho_seguro: break
                
                if vizinho_seguro:
                    fugas.append(d_nome)
        
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
    
    return f"C:{acima}_B:{abaixo}_E:{esquerda}_D:{direita}_Perigo:{em_perigo}_Fuga:{rota_fuga}_AlvoX:{dir_x}_AlvoY:{dir_y}_Dist:{dist_inimigo}"

def calcular_recompensa(estado_ant, acao_ant, estado_atual, self_state, mapa, jogadores):
    recompensa = -2  
    
    if not self_state['ativo']:
        return -1000

    bateu_parede = False
    if acao_ant == "cima" and ("C:1" in estado_ant or "C:2" in estado_ant): bateu_parede = True
    if acao_ant == "baixo" and ("B:1" in estado_ant or "B:2" in estado_ant): bateu_parede = True
    if acao_ant == "esquerda" and ("E:1" in estado_ant or "E:2" in estado_ant): bateu_parede = True
    if acao_ant == "direita" and ("D:1" in estado_ant or "D:2" in estado_ant): bateu_parede = True

    if bateu_parede:
        recompensa -= 5  
        
    if "Perigo:N" in estado_ant and "Perigo:S" in estado_atual and acao_ant != "bomba":
        recompensa -= 200  
        
    if "Perigo:S" in estado_atual:
        if "Fuga:Nenhuma" in estado_atual and "Dist:Perto" not in estado_atual:
            recompensa -= 100  
        else:
            recompensa -= 30   
            
    if "Perigo:S" in estado_ant:
        if "Fuga:NA" not in estado_ant and "Fuga:Nenhuma" not in estado_ant:
            direcao_fuga = estado_ant.split("Fuga:")[1].split("_")[0]
            mapa_fugas = {"C": "cima", "B": "baixo", "E": "esquerda", "D": "direita"}
            if mapa_fugas.get(direcao_fuga) == acao_ant:
                recompensa += 50  
        elif acao_ant == "parado" and not bateu_parede:
            recompensa += 30      

    if "Perigo:N" in estado_ant and acao_ant == "parado":
        recompensa -= 15  

    # --- A FOME (MODO PREDADOR) ---
    if "Dist:Longe" in estado_atual:
        recompensa -= 5

    elif acao_ant in ["cima", "baixo", "esquerda", "direita"]:
        if acao_ant == "cima" and ("C:3" in estado_ant or "C:4" in estado_ant): recompensa += 150
        elif acao_ant == "baixo" and ("B:3" in estado_ant or "B:4" in estado_ant): recompensa += 150
        elif acao_ant == "esquerda" and ("E:3" in estado_ant or "E:4" in estado_ant): recompensa += 150
        elif acao_ant == "direita" and ("D:3" in estado_ant or "D:4" in estado_ant): recompensa += 150

        alvo_x = estado_ant.split("AlvoX:")[1].split("_")[0]
        alvo_y = estado_ant.split("AlvoY:")[1].split("_")[0]
        
        indo_para_alvo = (
            (acao_ant == "cima" and alvo_y == "C") or
            (acao_ant == "baixo" and alvo_y == "B") or
            (acao_ant == "esquerda" and alvo_x == "E") or
            (acao_ant == "direita" and alvo_x == "D")
        )
        
        if indo_para_alvo and not bateu_parede:
            recompensa += 40
        elif alvo_x != "Igual" or alvo_y != "Igual":
            recompensa -= 4  

    elif acao_ant == "bomba":
        # Usa .get() para buscar o limite de bombas ou trava em 1 por segurança
        if self_state['bombas_ativas'] >= self_state.get('bombas_maximas', 1):
             recompensa -= 500
        elif "Perigo:S" in estado_ant or "Fuga:Nenhuma" in estado_ant:
            recompensa -= 500
        else:
            x = self_state['grid_x']
            y = self_state['grid_y']
            alcance = 1 + (self_state.get('bomba_nivel', 1) - 1) * 2
            
            alvos_atingidos = 0
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                for i in range(1, alcance + 1):
                    nx, ny = x + dx * i, y + dy * i
                    if 0 <= nx < 13 and 0 <= ny < 11:
                        if mapa[ny][nx] == 2:  
                            break
                        if mapa[ny][nx] == 1:  
                            alvos_atingidos += 1
                            break 
                        for p in jogadores:
                            if p.ativo and p.grid_x == nx and p.grid_y == ny:
                                alvos_atingidos += 3 
                                break
                    else:
                        break 
                        
            if alvos_atingidos > 0:
                recompensa += (100 * alvos_atingidos)  
                if "Dist:Perto" in estado_ant:
                    recompensa += 200  
            else:
                recompensa -= 10  
            
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
        # Equação de Bellman corrigida
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
            json.dump({"metadata": {"epsilon": EPSILON}, "q_table": q_table}, f)

    return acao_escolhida