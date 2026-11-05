import random
import json
import os
from collections import deque
from busca_caminho import calcular_distancias_mapa, encontrar_rota
from mapa_oficial import (
    BLOCO,
    PAREDE,
    POWERUP_BOMBA,
    POWERUP_FOGO,
    celula_caminhavel,
    coordenada_no_mapa,
)

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
objetivo_atual = None
posicao_objetivo_atual = None
distancia_objetivo_atual = None
posicao_jogador_anterior = None
metricas_rota = {
    "passos_avaliados_meta": 0,
    "passos_aproximando_meta": 0,
    "passos_afastando_meta": 0,
    "passos_neutros_meta": 0,
}
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


def consumir_metricas_rota():
    """Entrega e zera os contadores de rota do episódio encerrado."""
    global metricas_rota
    resultado = metricas_rota.copy()
    metricas_rota = {
        "passos_avaliados_meta": 0,
        "passos_aproximando_meta": 0,
        "passos_afastando_meta": 0,
        "passos_neutros_meta": 0,
    }
    return resultado

def resetar_episodio(morreu=False):
    global estado_anterior, acao_anterior, q_table, EPSILON
    global objetivo_atual, posicao_objetivo_atual, distancia_objetivo_atual
    global posicao_jogador_anterior
    if morreu and estado_anterior is not None and acao_anterior is not None:
        if estado_anterior not in q_table:
            q_table[estado_anterior] = {acao: 0.0 for acao in ACOES}
        q_antigo = q_table[estado_anterior][acao_anterior]
        q_table[estado_anterior][acao_anterior] = q_antigo + ALFA * (-500 - q_antigo)
        salvar_progresso()
    estado_anterior = None
    acao_anterior = None
    objetivo_atual = None
    posicao_objetivo_atual = None
    distancia_objetivo_atual = None
    posicao_jogador_anterior = None

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
                if not coordenada_no_mapa(mapa, nx, ny): break
                if mapa[ny][nx] == PAREDE: break
                perigo.add((nx, ny))
                if mapa[ny][nx] == BLOCO: break
    return perigo, ocupadas

def buscar_direcao_fuga_bfs(x, y, mapa, perigo, ocupadas, max_passos=25):
    direcoes = [("C", 0, -1), ("B", 0, 1), ("E", -1, 0), ("D", 1, 0)]
    centro_x = len(mapa[0]) // 2 if mapa else 0
    centro_y = len(mapa) // 2
    direcoes.sort(key=lambda d: abs((x + d[1]) - centro_x) + abs((y + d[2]) - centro_y))
    
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
            if coordenada_no_mapa(mapa, nx, ny):
                if (nx, ny) not in visitados and celula_caminhavel(mapa, nx, ny) and (nx, ny) not in ocupadas:
                    visitados.add((nx, ny))
                    passo_inicial = nome_dir if primeiro_passo is None else primeiro_passo
                    fila.append((nx, ny, passo_inicial, dist + 1))
    return "Nenhuma"

def calcular_farol_global(x, y, mapa, jogadores, objetivo_previo=None):
    direcoes = (("C", 0, -1), ("B", 0, 1), ("E", -1, 0), ("D", 1, 0))
    inimigos = {
        indice: (p.grid_x, p.grid_y)
        for indice, p in enumerate(jogadores)
        if p.ativo and (p.grid_x, p.grid_y) != (x, y)
        and celula_caminhavel(mapa, p.grid_x, p.grid_y)
    }
    powerups = [
        (col, row)
        for row, linha in enumerate(mapa)
        for col, terreno in enumerate(linha)
        if terreno in (POWERUP_BOMBA, POWERUP_FOGO) and (col, row) != (x, y)
    ]

    # Mantém a classificação antiga para não alterar a condição de bombas.
    alvos_proximidade = list(inimigos.values()) + powerups
    menor_manhattan = min(
        (abs(ax - x) + abs(ay - y) for ax, ay in alvos_proximidade),
        default=9999,
    )
    dist_inimigo = "Perto" if menor_manhattan <= 3 else "Medio" if menor_manhattan <= 7 else "Longe"

    distancias_desde_ia = calcular_distancias_mapa(mapa, [(x, y)])
    distancias_ate_inimigos = calcular_distancias_mapa(mapa, inimigos.values())
    distancia_inimigo = distancias_ate_inimigos.get((x, y))

    def posicao_do_objetivo(chave):
        if not chave:
            return None
        if chave[0] == "jogador":
            indice = chave[1]
            if indice in inimigos:
                return inimigos[indice]
        elif chave[0] == "powerup":
            posicao = (chave[1], chave[2])
            if posicao in powerups:
                return posicao
        return None

    # Mantém a meta enquanto ela existir e continuar alcançável.
    alvo = posicao_do_objetivo(objetivo_previo)
    chave_objetivo = objetivo_previo if alvo in distancias_desde_ia else None

    if chave_objetivo is None:
        if distancia_inimigo is not None:
            powerups_no_caminho = []
            for posicao in powerups:
                distancia_desde_ia = distancias_desde_ia.get(posicao)
                distancia_ate_inimigo = distancias_ate_inimigos.get(posicao)
                if distancia_desde_ia is None or distancia_ate_inimigo is None:
                    continue
                desvio = distancia_desde_ia + distancia_ate_inimigo - distancia_inimigo
                if desvio <= 2:
                    powerups_no_caminho.append((distancia_desde_ia, desvio, posicao))

            if powerups_no_caminho:
                _, _, alvo = min(powerups_no_caminho)
                chave_objetivo = ("powerup", alvo[0], alvo[1])
            else:
                inimigo_mais_proximo = min(
                    (distancias_desde_ia[posicao], indice, posicao)
                    for indice, posicao in inimigos.items()
                    if posicao in distancias_desde_ia
                )
                _, indice, alvo = inimigo_mais_proximo
                chave_objetivo = ("jogador", indice)
        else:
            powerups_alcancaveis = [
                (distancias_desde_ia[posicao], posicao)
                for posicao in powerups
                if posicao in distancias_desde_ia
            ]
            if powerups_alcancaveis:
                _, alvo = min(powerups_alcancaveis)
                chave_objetivo = ("powerup", alvo[0], alvo[1])

    if chave_objetivo is None or alvo is None:
        return "Igual", "Igual", dist_inimigo, None, None, None

    rota = encontrar_rota(mapa, (x, y), alvo)
    distancia_rota = len(rota) - 1 if rota else None
    melhor_dir = None
    if len(rota) > 1:
        proximo_x, proximo_y = rota[1]
        deslocamento = (proximo_x - x, proximo_y - y)
        melhor_dir = next(
            (nome for nome, dx, dy in direcoes if (dx, dy) == deslocamento),
            None,
        )

    direcao_x = "D" if melhor_dir == "D" else "E" if melhor_dir == "E" else "Igual"
    direcao_y = "B" if melhor_dir == "B" else "C" if melhor_dir == "C" else "Igual"
    return direcao_x, direcao_y, dist_inimigo, chave_objetivo, alvo, distancia_rota

def obter_estado_simplificado(self_state, mapa, bombas, jogadores):
    global objetivo_atual, posicao_objetivo_atual, distancia_objetivo_atual
    x, y = self_state["grid_x"], self_state["grid_y"]
    def ver_celula(nx, ny):
        return mapa[ny][nx] if coordenada_no_mapa(mapa, nx, ny) else PAREDE
    
    acima, abaixo, esquerda, direita = ver_celula(x, y - 1), ver_celula(x, y + 1), ver_celula(x - 1, y), ver_celula(x + 1, y)
    perigo, ocupadas = mapear_zonas_perigo(mapa, bombas)
    em_perigo = "S" if (x, y) in perigo else "N"
    rota_fuga = buscar_direcao_fuga_bfs(x, y, mapa, perigo, ocupadas) if em_perigo == "S" else "NA"
    (
        dir_x, dir_y, dist_inimigo, objetivo_atual,
        posicao_objetivo_atual, distancia_objetivo_atual,
    ) = calcular_farol_global(x, y, mapa, jogadores, objetivo_atual)
    
    return f"C:{acima}_B:{abaixo}_E:{esquerda}_D:{direita}_Perigo:{em_perigo}_Fuga:{rota_fuga}_AlvoX:{dir_x}_AlvoY:{dir_y}_Dist:{dist_inimigo}"

def calcular_recompensa(
    estado_ant, acao_ant, estado_atual, self_state, mapa, bombas, jogadores,
    jogador_ia=None, progresso_objetivo=None,
):
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

        if not bateu_parede:
            recompensa -= 2

        if progresso_objetivo is not None:
            if progresso_objetivo > 0:
                recompensa += 4
            elif progresso_objetivo < 0:
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
                    if p is not jogador_ia and p.ativo and p.grid_x == x and p.grid_y == y:
                        alvos_inimigo += 1

                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    for i in range(1, alcance + 1):
                        nx, ny = x + dx * i, y + dy * i
                        if coordenada_no_mapa(mapa, nx, ny):
                            if mapa[ny][nx] == PAREDE: break
                            if mapa[ny][nx] == BLOCO:
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
        livres = [a for a, (dx, dy) in direcoes.items() if celula_caminhavel(mapa, x + dx, y + dy)]
        return livres if livres else ACOES

    acoes_validas = []
    for a, (dx, dy) in direcoes.items():
        nx, ny = x + dx, y + dy
        if celula_caminhavel(mapa, nx, ny) and (nx, ny) not in perigo and (nx, ny) not in ocupadas:
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
            if coordenada_no_mapa(mapa, nx, ny):
                if mapa[ny][nx] == PAREDE: break 
                if mapa[ny][nx] == BLOCO or dist_inimigo == "Perto": 
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
    global objetivo_atual, posicao_objetivo_atual, distancia_objetivo_atual
    global posicao_jogador_anterior

    objetivo_previo = objetivo_atual
    posicao_jogador_atual = (self_state["grid_x"], self_state["grid_y"])
    estado_atual = obter_estado_simplificado(self_state, mapa, bombas, jogadores)
    progresso_objetivo = None
    if (
        objetivo_previo is not None
        and objetivo_previo == objetivo_atual
        and posicao_objetivo_atual is not None
        and distancia_objetivo_atual is not None
        and posicao_jogador_anterior is not None
    ):
        distancias_ate_alvo_atual = calcular_distancias_mapa(
            mapa, [posicao_objetivo_atual]
        )
        distancia_anterior_ate_alvo_atual = distancias_ate_alvo_atual.get(
            posicao_jogador_anterior
        )
        if distancia_anterior_ate_alvo_atual is not None:
            progresso_objetivo = (
                distancia_anterior_ate_alvo_atual - distancia_objetivo_atual
            )

    if acao_anterior in ("cima", "baixo", "esquerda", "direita") and progresso_objetivo is not None:
        metricas_rota["passos_avaliados_meta"] += 1
        if progresso_objetivo > 0:
            metricas_rota["passos_aproximando_meta"] += 1
        elif progresso_objetivo < 0:
            metricas_rota["passos_afastando_meta"] += 1
        else:
            metricas_rota["passos_neutros_meta"] += 1

    if estado_atual not in q_table:
        q_table[estado_atual] = {acao: 0.0 for acao in ACOES}
        
    if estado_anterior is not None and acao_anterior is not None:
        recompensa = calcular_recompensa(
            estado_anterior, acao_anterior, estado_atual,
            self_state, mapa, bombas, jogadores,
            jogador_ia=player, progresso_objetivo=progresso_objetivo,
        )
        q_antigo = q_table[estado_anterior][acao_anterior]
        max_q_futuro = max(q_table[estado_atual].values())
        q_table[estado_anterior][acao_anterior] = q_antigo + ALFA * (recompensa + GAMA * max_q_futuro - q_antigo)

    x, y = self_state["grid_x"], self_state["grid_y"]
    acoes_candidatas = obter_acoes_seguras(x, y, estado_atual, self_state, mapa, bombas)

    if random.uniform(0, 1) < EPSILON:
        acao_escolhida = random.choice(acoes_candidatas)
    else:
        maior_valor = max(q_table[estado_atual].get(a, 0.0) for a in acoes_candidatas)
        melhores_acoes = [
            a for a in acoes_candidatas
            if q_table[estado_atual].get(a, 0.0) == maior_valor
        ]
        acao_escolhida = random.choice(melhores_acoes)

    if EPSILON > EPSILON_MIN: EPSILON *= EPSILON_DECAY

    estado_anterior, acao_anterior = estado_atual, acao_escolhida
    posicao_jogador_anterior = posicao_jogador_atual

    passos += 1
    # Expandido para 15000 para evitar gargalo de I/O em disco
    if passos % 15000 == 0:
        salvar_progresso()

    return acao_escolhida
