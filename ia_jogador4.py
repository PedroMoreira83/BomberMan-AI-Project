import random
import json
import os

ALFA = 0.1      
GAMA = 0.9      
EPSILON = 1.0         # Começa 100% aleatório (fase de exploração)
EPSILON_MIN = 0.05    # Nunca desce de 5% de aleatoriedade
# Mude a taxa de decaimento para ser extremamente lenta
EPSILON_DECAY = 0.99999 # Antes era 0.999

ACOES = ["cima", "baixo", "esquerda", "direita", "bomba", "parado"]
ARQUIVO_MEMORIA = "q_table_j4.json" # MUDE ISSO EM CADA ARQUIVO DE JOGADOR

q_table = {}
estado_anterior = None
acao_anterior = None
passos = 0 # Usado para não sobrecarregar o disco rígido

# Carrega a memória de treinamentos anteriores ao abrir o jogo
if os.path.exists(ARQUIVO_MEMORIA):
    with open(ARQUIVO_MEMORIA, "r") as f:
        q_table = json.load(f)

def obter_estado_simplificado(self_state, mapa, bombas):
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
    
    # NOVA LÓGICA DE VISÃO DE PERIGO
    em_perigo = "N"
    for b in bombas:
        if not b.explodida:
            # Se a IA está na mesma linha ou coluna de uma bomba
            if b.x == x or b.y == y:
                # Verifica a distância. Uma bomba nível 1 afeta 1 bloco de distância. Nível 2 afeta 3 blocos.
                alcance = 1 + (b.nivel - 1) * 2
                distancia = abs(b.x - x) + abs(b.y - y)
                if distancia <= alcance:
                    em_perigo = "S"
                    break

    bombas_ativas = self_state['bombas_ativas']
    
    # Adicionamos o "Perigo" à string de estado
    return f"C:{acima}_B:{abaixo}_E:{esquerda}_D:{direita}_Bomb:{bombas_ativas}_Perigo:{em_perigo}"

def calcular_recompensa(estado_ant, acao_ant, estado_atual, self_state, mapa):
    recompensa = -1  # Custo de vida padrão (força a IA a agir rápido)
    x = self_state['grid_x']
    y = self_state['grid_y']
    
    # 1. Punição massiva por morte
    if not self_state['ativo']:
        return -1000

    # 2. Punição por bater na parede (andou mas continuou no mesmo estado)
    if acao_ant in ["cima", "baixo", "esquerda", "direita"] and estado_ant == estado_atual:
        recompensa -= 10
        
    # 3. ANTI-CAMPING: Punição por ficar parado sem necessidade
    elif acao_ant == "parado":
        if "Perigo:S" in estado_atual:
            recompensa -= 50  # Ficar parado na reta da bomba é suicídio!
        else:
            recompensa -= 5   # Ficar parado sem fazer nada atrasa o jogo
            
    # 4. FARO DE CAÇA: Incentivo de aproximação aos blocos destrutíveis
    elif acao_ant in ["cima", "baixo", "esquerda", "direita"]:
        # Conta quantos blocos destrutíveis (código 1) estão na visão imediata do estado
        direcoes_blocos = ["C:1", "B:1", "E:1", "D:1"]
        blocos_ant = sum([1 for d in direcoes_blocos if d in estado_ant])
        blocos_atual = sum([1 for d in direcoes_blocos if d in estado_atual])
        
        if blocos_atual > blocos_ant:
            recompensa += 10  # Reforço positivo forte: achou um caminho para o alvo!
        elif blocos_atual < blocos_ant:
            recompensa -= 2   # Reforço negativo leve: está se afastando de um alvo.

    # 5. ASSERITIVIDADE DA BOMBA: Punição severa por erro, recompensa múltipla por acerto
    elif acao_ant == "bomba":
        alvos_atingidos = 0
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 13 and 0 <= ny < 11:
                if mapa[ny][nx] == 1:
                    alvos_atingidos += 1
                    
        if alvos_atingidos > 0:
            recompensa += (50 * alvos_atingidos)  
        else:
            recompensa -= 100  
            
    return recompensa

def decidir_acao(player, mapa, jogadores, bombas, tempo_restante, pontos, hud_info, self_state):
    global q_table, estado_anterior, acao_anterior, EPSILON, passos
    
    estado_atual = obter_estado_simplificado(self_state, mapa, bombas)
    
    if estado_atual not in q_table:
        q_table[estado_atual] = {acao: 0.0 for acao in ACOES}
        
    if estado_anterior is not None and acao_anterior is not None:
        recompensa = calcular_recompensa(estado_anterior, acao_anterior, estado_atual, self_state, mapa)
        q_antigo = q_table[estado_anterior][acao_anterior]
        max_q_futuro = max(q_table[estado_atual].values())
        q_table[estado_anterior][acao_anterior] = q_antigo + ALFA * (recompensa + GAMA * max_q_futuro - q_antigo)

    # Lógica de Decisão (Exploração Aleatória vs Inteligência Gravada)
    if random.uniform(0, 1) < EPSILON:
        acao_escolhida = random.choice(ACOES)
    else:
        acao_escolhida = max(q_table[estado_atual], key=q_table[estado_atual].get)

    # Reduz a aleatoriedade para o próximo frame
    if EPSILON > EPSILON_MIN:
        EPSILON *= EPSILON_DECAY

    estado_anterior = estado_atual
    acao_anterior = acao_escolhida

    # Salva o arquivo no disco a cada 100 frames para evitar gargalo de I/O no Windows
    passos += 1
    if passos % 100 == 0:
        with open(ARQUIVO_MEMORIA, "w") as f:
            json.dump(q_table, f)

    return acao_escolhida