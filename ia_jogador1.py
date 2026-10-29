import random
import json
import os
from collections import deque
from heapq import heappop, heappush

try:
    from aglutinador_memoria import aglutinar_todos_arquivos, higienizar_acoes_fisicas
    TEM_AGLUTINADOR = True
except ImportError:
    TEM_AGLUTINADOR = False

ALFA = 0.15      
GAMA = 0.95           
EPSILON = 0.15        
EPSILON_MIN = 0.05    
EPSILON_DECAY = 0.9995 

ACOES = ["cima", "baixo", "esquerda", "direita", "bomba", "parado"]
ARQUIVO_MEMORIA = "q_table_j1.json" 

q_table = {}
estado_anterior = None
acao_anterior = None
passos = 0 

if TEM_AGLUTINADOR:
    q_table = aglutinar_todos_arquivos("*.json")

if os.path.exists(ARQUIVO_MEMORIA):
    try:
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
            dados = json.load(f)
            if "metadata" in dados:
                EPSILON = dados["metadata"].get("epsilon", EPSILON)
                tabela_local = dados.get("q_table", {})
            else:
                tabela_local = dados
            if not q_table:
                q_table = tabela_local
    except Exception:
        pass

def salvar_progresso():
    try:
        with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
            json.dump({"metadata": {"epsilon": EPSILON}, "q_table": q_table}, f)
        if TEM_AGLUTINADOR:
            aglutinar_todos_arquivos("*.json")
    except Exception:
        pass

def resetar_episodio(morreu=False):
    global estado_anterior, acao_anterior, q_table, EPSILON
    if morreu and estado_anterior is not None and acao_anterior is not None:
        if estado_anterior not in q_table:
            q_table[estado_anterior] = {acao: 0.0 for acao in ACOES}
        q_antigo = q_table[estado_anterior][acao_anterior]
        q_table[estado_anterior][acao_anterior] = q_antigo + ALFA * (-500 - q_antigo)
        salvar_progresso()
    estado_anterior = None
    acao_anterior = None

def mapear_zonas_perigo(mapa, bombas, bomba_extra=None):
    perigo = set()
    ocupadas = set()
    lista_bombas = list(bombas)
    if bomba_extra is not None:
        lista_bombas.append(bomba_extra)

    for b in lista_bombas:
        if getattr(b, "explodida", False):
            for fx, fy in getattr(b, "fogo", []):
                perigo.add((fx, fy))
            continue
            
        ocupadas.add((b.x, b.y))
        perigo.add((b.x, b.y))
        alcance = 1 + (getattr(b, "nivel", 1) - 1) * 2
        
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            for i in range(1, alcance + 1):
                nx, ny = b.x + dx * i, b.y + dy * i
                if not (0 <= nx < 13 and 0 <= ny < 11): break
                if mapa[ny][nx] == 2: break
                perigo.add((nx, ny))
                if mapa[ny][nx] == 1: break
    return perigo, ocupadas

def buscar_direcao_fuga_bfs(x, y, mapa, perigo, ocupadas, max_passos=25):
    direcoes = [("C", 0, -1), ("B", 0, 1), ("E", -1, 0), ("D", 1, 0)]
    direcoes.sort(key=lambda d: abs((x + d[1]) - 6) + abs((y + d[2]) - 5))
    
    fila = deque([(x, y, None, 0)])
    visitados = {(x, y)}

    while fila:
        cx, cy, primeiro_passo, dist = fila.popleft()
        if (cx, cy) not in perigo and primeiro_passo is not None:
            return primeiro_passo
        if dist >= max_passos:
            continue

        for nome_dir, dx, dy in direcoes:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < 13 and 0 <= ny < 11:
                if (nx, ny) not in visitados and mapa[ny][nx] in (0, 3, 4) and (nx, ny) not in ocupadas:
                    visitados.add((nx, ny))
                    passo_inicial = nome_dir if primeiro_passo is None else primeiro_passo
                    fila.append((nx, ny, passo_inicial, dist + 1))
    return "Nenhuma"

def calcular_farol_global(x, y, mapa, jogadores, peso_tijolo=4):
    alvos = [(p.grid_x, p.grid_y) for p in jogadores if p.ativo and (p.grid_x != x or p.grid_y != y)]
    
    for row in range(len(mapa)):
        for col in range(len(mapa[row])):
            if mapa[row][col] in (3, 4):
                alvos.append((col, row))
                
    if not alvos: return "Igual", "Igual", "Longe"

    dist = {}
    fila = []
    for ax, ay in alvos:
        dist[(ax, ay)] = 0
        heappush(fila, (0, ax, ay))

    while fila:
        custo, cx, cy = heappop(fila)
        if custo > dist.get((cx, cy), 9999): continue
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < 13 and 0 <= ny < 11 and mapa[ny][nx] != 2:
                passo_custo = peso_tijolo if mapa[ny][nx] == 1 else 1
                novo_custo = custo + passo_custo
                if novo_custo < dist.get((nx, ny), 9999):
                    dist[(nx, ny)] = novo_custo
                    heappush(fila, (novo_custo, nx, ny))

    menor_manhattan = min(abs(ax - x) + abs(ay - y) for ax, ay in alvos)
    dist_inimigo = "Perto" if menor_manhattan <= 3 else "Medio" if menor_manhattan <= 7 else "Longe"

    melhor_custo = dist.get((x, y), 9999)
    melhor_dir = None
    for nome_dir, dx, dy in (("C", 0, -1), ("B", 0, 1), ("E", -1, 0), ("D", 1, 0)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < 13 and 0 <= ny < 11 and mapa[ny][nx] != 2:
            c_viz = dist.get((nx, ny), 9999)
            if c_viz < melhor_custo:
                melhor_custo = c_viz
                melhor_dir = nome_dir

    if melhor_dir == "D": return "D", "Igual", dist_inimigo
    if melhor_dir == "E": return "E", "Igual", dist_inimigo
    if melhor_dir == "B": return "Igual", "B", dist_inimigo
    if melhor_dir == "C": return "Igual", "C", dist_inimigo

    alvo_prox = min(alvos, key=lambda a: abs(a[0] - x) + abs(a[1] - y))
    dir_x = "D" if alvo_prox[0] > x else "E" if alvo_prox[0] < x else "Igual"
    dir_y = "B" if alvo_prox[1] > y else "C" if alvo_prox[1] < y else "Igual"
    return dir_x, dir_y, dist_inimigo

def obter_estado_simplificado(self_state, mapa, bombas, jogadores):
    x, y = self_state["grid_x"], self_state["grid_y"]
    def ver_celula(nx, ny):
        return mapa[ny][nx] if 0 <= nx < 13 and 0 <= ny < 11 else 2  
    
    acima, abaixo, esquerda, direita = ver_celula(x, y - 1), ver_celula(x, y + 1), ver_celula(x - 1, y), ver_celula(x + 1, y)
    perigo, ocupadas = mapear_zonas_perigo(mapa, bombas)
    em_perigo = "S" if (x, y) in perigo else "N"
    rota_fuga = buscar_direcao_fuga_bfs(x, y, mapa, perigo, ocupadas) if em_perigo == "S" else "NA"
    dir_x, dir_y, dist_inimigo = calcular_farol_global(x, y, mapa, jogadores)
    
    return f"C:{acima}_B:{abaixo}_E:{esquerda}_D:{direita}_Perigo:{em_perigo}_Fuga:{rota_fuga}_AlvoX:{dir_x}_AlvoY:{dir_y}_Dist:{dist_inimigo}"

def calcular_recompensa(estado_ant, acao_ant, estado_atual, self_state, mapa, bombas, jogadores):
    if not self_state["ativo"]: return -500
    recompensa = -0.5

    bateu_parede = (
        (acao_ant == "cima" and ("C:1" in estado_ant or "C:2" in estado_ant)) or
        (acao_ant == "baixo" and ("B:1" in estado_ant or "B:2" in estado_ant)) or
        (acao_ant == "esquerda" and ("E:1" in estado_ant or "E:2" in estado_ant)) or
        (acao_ant == "direita" and ("D:1" in estado_ant or "D:2" in estado_ant))
    )
    if bateu_parede: recompensa -= 15

    if "Perigo:N" in estado_ant and "Perigo:S" in estado_atual and acao_ant != "bomba":
        recompensa -= 150

    if "Perigo:S" in estado_ant:
        direcao_fuga = estado_ant.split("Fuga:")[1].split("_")[0]
        mapa_fugas = {"C": "cima", "B": "baixo", "E": "esquerda", "D": "direita"}
        
        if mapa_fugas.get(direcao_fuga) == acao_ant:
            recompensa += 5
        elif acao_ant != "bomba":
            recompensa -= 40
            
        if "Perigo:N" in estado_atual:
            recompensa += 10

    if acao_ant == "parado":
        if "Perigo:N" in estado_ant and (self_state.get("bombas_ativas", 0) > 0 or len(bombas) > 0):
            recompensa += 2
        else:
            recompensa -= 15

    elif acao_ant in ["cima", "baixo", "esquerda", "direita"] and "Perigo:N" in estado_ant:
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
            recompensa += 8
        elif not bateu_parede:
            recompensa -= 1

        if not bateu_parede:
            recompensa -= 2

    elif acao_ant == "bomba":
        limite_bombas = 1
        for key in ["bombas_limite", "max_bombas", "limite_bombas", "bomba_qtd", "bombas_maximas", "quantidade_bombas", "bombas_inventario"]:
            if key in self_state:
                limite_bombas = self_state[key]
                break

        if "Perigo:S" in estado_ant or self_state.get("bombas_ativas", 0) >= limite_bombas:
            recompensa -= 150
        else:
            fuga_apos_plantar = estado_atual.split("Fuga:")[1].split("_")[0]
            if fuga_apos_plantar == "Nenhuma":
                recompensa -= 300
            else:
                x, y = self_state["grid_x"], self_state["grid_y"]
                nivel = self_state.get("bomba_nivel", 1)
                alcance = 1 + (nivel - 1) * 2

                alvos_tijolo = 0
                alvos_inimigo = 0
                for p in jogadores:
                    if p.ativo and p.grid_x == x and p.grid_y == y:
                        alvos_inimigo += 1

                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    for i in range(1, alcance + 1):
                        nx, ny = x + dx * i, y + dy * i
                        if 0 <= nx < 13 and 0 <= ny < 11:
                            if mapa[ny][nx] == 2: break
                            if mapa[ny][nx] == 1:
                                alvos_tijolo += 1
                                break
                            for p in jogadores:
                                if p.ativo and p.grid_x == nx and p.grid_y == ny:
                                    alvos_inimigo += 1
                                    break
                        else: break

                if alvos_tijolo > 0 or alvos_inimigo > 0:
                    recompensa += (150 * alvos_tijolo) + (500 * alvos_inimigo)
                else:
                    recompensa -= 40

    return recompensa

def obter_acoes_seguras(x, y, estado_atual, self_state, mapa, bombas):
    perigo, ocupadas = mapear_zonas_perigo(mapa, bombas)
    direcoes = {"cima": (0, -1), "baixo": (0, 1), "esquerda": (-1, 0), "direita": (1, 0)}

    if (x, y) in perigo:
        fuga_bfs = buscar_direcao_fuga_bfs(x, y, mapa, perigo, ocupadas)
        mapa_fugas = {"C": "cima", "B": "baixo", "E": "esquerda", "D": "direita"}
        if fuga_bfs in mapa_fugas:
            return [mapa_fugas[fuga_bfs]]
        livres = [a for a, (dx, dy) in direcoes.items() if 0 <= x + dx < 13 and 0 <= y + dy < 11 and mapa[y + dy][x + dx] in (0, 3, 4)]
        return livres if livres else ACOES

    acoes_validas = []
    for a, (dx, dy) in direcoes.items():
        nx, ny = x + dx, y + dy
        if 0 <= nx < 13 and 0 <= ny < 11 and mapa[ny][nx] in (0, 3, 4) and (nx, ny) not in perigo and (nx, ny) not in ocupadas:
            acoes_validas.append(a)

    limite_bombas = 1
    for key in ["bombas_limite", "max_bombas", "limite_bombas", "bomba_qtd", "bombas_maximas", "quantidade_bombas", "bombas_inventario"]:
        if key in self_state:
            limite_bombas = self_state[key]
            break

    nivel = self_state.get("bomba_nivel", 1)
    alcance = 1 + (nivel - 1) * 2
    dist_inimigo = estado_atual.split("Dist:")[1]
    tem_alvo_util = False
    
    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        for i in range(1, alcance + 1):
            nx, ny = x + dx * i, y + dy * i
            if 0 <= nx < 13 and 0 <= ny < 11:
                if mapa[ny][nx] == 2: break 
                if mapa[ny][nx] == 1 or dist_inimigo == "Perto": 
                    tem_alvo_util = True
                    break
            else: break
            
    if tem_alvo_util and self_state.get("bombas_ativas", 0) < limite_bombas:
        class BombaSimulada:
            def __init__(self, bx, by, n):
                self.x, self.y, self.nivel, self.explodida = bx, by, n, False
        p_sim, o_sim = mapear_zonas_perigo(mapa, bombas, BombaSimulada(x, y, nivel))
        if buscar_direcao_fuga_bfs(x, y, mapa, p_sim, o_sim) != "Nenhuma":
            acoes_validas.append("bomba")

    if not acoes_validas or len(bombas) > 0:
        acoes_validas.append("parado")

    return acoes_validas if acoes_validas else ["parado"]

def decidir_acao(player, mapa, jogadores, bombas, tempo_restante, pontos, hud_info, self_state):
    global q_table, estado_anterior, acao_anterior, EPSILON, passos
    
    estado_atual = obter_estado_simplificado(self_state, mapa, bombas, jogadores)
    if estado_atual not in q_table:
        q_table[estado_atual] = {acao: 0.0 for acao in ACOES}
        
    if estado_anterior is not None and acao_anterior is not None:
        recompensa = calcular_recompensa(estado_anterior, acao_anterior, estado_atual, self_state, mapa, bombas, jogadores)
        q_antigo = q_table[estado_anterior][acao_anterior]
        max_q_futuro = max(q_table[estado_atual].values())
        q_table[estado_anterior][acao_anterior] = q_antigo + ALFA * (recompensa + GAMA * max_q_futuro - q_antigo)

    x, y = self_state["grid_x"], self_state["grid_y"]
    acoes_candidatas = obter_acoes_seguras(x, y, estado_atual, self_state, mapa, bombas)

    if random.uniform(0, 1) < EPSILON:
        acao_escolhida = random.choice(acoes_candidatas)
    else:
        acao_escolhida = max(acoes_candidatas, key=lambda a: q_table[estado_atual].get(a, 0.0))

    if EPSILON > EPSILON_MIN: EPSILON *= EPSILON_DECAY

    estado_anterior, acao_anterior = estado_atual, acao_escolhida

    passos += 1
    # Expandido para 15000 para evitar gargalo de I/O em disco
    if passos % 15000 == 0:
        salvar_progresso()

    return acao_escolhida