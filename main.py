import pygame
import sys
import importlib
import random
import hashlib
import json
import csv
import os

from ia_chefao import decidir_acao as ia_do_colega

def gerar_checksum_dados(obj):
    def simplificar(o):
        if isinstance(o, list):
            return [simplificar(x) for x in o]
        elif isinstance(o, dict):
            return {k: simplificar(v) for k, v in o.items()}
        elif hasattr(o, '__dict__'):
            if isinstance(o, Player):
                return {
                    'grid_x': o.grid_x, 'grid_y': o.grid_y,
                    'max_bombas': o.max_bombas, 'bomba_nivel': o.bomba_nivel,
                    'ativo': o.ativo, 'time': o.time
                }
            elif isinstance(o, Bomba):
                return {
                    'x': o.x, 'y': o.y, 'nivel': o.nivel,
                    'explodida': o.explodida, 'tempo_explosao': o.tempo_explosao,
                    'tempo_fogo': o.tempo_fogo, 'fogo': o.fogo
                }
            else:
                return str(o)
        else:
            return o

    dados_simplificados = simplificar(obj)
    json_data = json.dumps(dados_simplificados, sort_keys=True)
    return hashlib.md5(json_data.encode()).hexdigest()

pygame.init()

# Parâmetros de jogo
TILE_SIZE = 48
ROWS, COLS = 11, 13
HUD_HEIGHT = 60
WIDTH, HEIGHT = COLS * TILE_SIZE, ROWS * TILE_SIZE
TEMPO_MOVIMENTO = 0.1
TEMPO_EXPLOSAO = 4
TEMPO_FOGO = 0.5
MAX_BOMBAS = 5
TEMPO_PARTIDA = 180

PONTOS_BLOCO = 100
PONTOS_POWERUP_COLETADO = 200
PONTOS_POWERUP_DESTRUIDO = -50
PONTOS_MATAR_JOGADOR = 1000
PONTOS_VITORIA = 10000

PROB_BOMBA = 0.12
PROB_FOGO = 0.10

screen = pygame.display.set_mode((WIDTH, HEIGHT + HUD_HEIGHT))
pygame.display.set_caption("Bomberman Arena")

COLOR_BG = (20, 20, 20)
COLOR_GRASS = (80, 150, 80)
COLOR_FLOOR = (160,82,45)
COLOR_BREAKABLE = (100, 100, 100)
COLOR_INDESTRUCTIBLE = (60, 60, 60)
COLOR_PLAYERS = [(0, 200, 255), (255, 100, 100), (200, 255, 100), (255, 255, 0), (255, 255, 255)]

# --- INICIALIZAÇÃO DE FONTES PARA O HUD ---
pygame.font.init()
font = pygame.font.SysFont("Arial", 16)
font_vitoria = pygame.font.SysFont("Arial", 20, bold=True)
fonte_pequena = pygame.font.SysFont("arial", 20)
fonte_grande = pygame.font.SysFont("arial", 60, bold=True)

try:
    powerup_bomba_img = pygame.transform.scale(pygame.image.load("pu_bomb.jpg"), (TILE_SIZE, TILE_SIZE))
    powerup_fogo_img = pygame.transform.scale(pygame.image.load("pu_fire.jpg"), (TILE_SIZE, TILE_SIZE))
    bloco_img = pygame.transform.scale(pygame.image.load("bloco.jpg"), (TILE_SIZE, TILE_SIZE))

    bomba_sprite = pygame.image.load("sprite_bomb_no_bg.png")
    bomb_frames = [
        pygame.transform.scale(bomba_sprite.subsurface(pygame.Rect(i * 48, 0, 48, 48)), (TILE_SIZE, TILE_SIZE))
        for i in range(3)
    ]

    explosao_sprite = pygame.image.load("sprite_explosao.png").convert_alpha()
    explosao_frames = [
        explosao_sprite.subsurface(pygame.Rect(i * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
        for i in range(5)
    ]
except pygame.error as e:
    print(f"Aviso: Não foi possível carregar as imagens ({e}). Usando retângulos coloridos como fallback temporário (caso suporte).")


mapa_base = [
    [0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0],
    [0, 2, 1, 2, 0, 2, 0, 2, 1, 2, 1, 2, 0],
    [1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1],
    [0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1],
    [1, 2, 0, 2, 1, 2, 0, 2, 1, 2, 1, 2, 1],
    [1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1],
    [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1],
    [0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
    [0, 2, 1, 2, 0, 2, 1, 2, 0, 2, 0, 2, 0],
    [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
]

# Copia para não perder o layout inicial ao resetar o episódio
mapa = [linha[:] for linha in mapa_base]

def criar_powerup(x, y, prob_bomba=PROB_BOMBA, prob_fogo=PROB_FOGO):
    r = random.random()
    if r < prob_bomba: return 3
    elif r < prob_bomba + prob_fogo: return 4
    return 0

def desenhar_hud(pontos, tempo_restante, partidas_jogadas):
    pygame.draw.rect(screen, (30, 30, 30), (0, 0, WIDTH, HUD_HEIGHT))
    
    # Textos do jogo base
    tempo_txt = font.render(f"Tempo: {int(tempo_restante)}s", True, (255, 255, 255))
    screen.blit(tempo_txt, (10, 10))
    nomes = [p1, p2, p3, p4, p5]
    for i, p in enumerate(players):
        if i >= len(nomes): break
        cor = COLOR_PLAYERS[i]
        txt = font.render(f"{nomes[i]}: {pontos[i]}", True, cor if p.ativo else (100, 100, 100))
        screen.blit(txt, (150 + i * 120, 10))

    # --- INCLUSÃO DO CONTADOR DE PARTIDAS E DICA DE TREINO ---
    texto_partidas = fonte_pequena.render(f"Partidas: {partidas_jogadas}", True, (255, 255, 255))
    screen.blit(texto_partidas, (10, HUD_HEIGHT - 25))

    texto_dica = fonte_pequena.render("Aperte F12 para o Modo Treino", True, (200, 200, 200))
    screen.blit(texto_dica, (WIDTH - texto_dica.get_width() - 10, HUD_HEIGHT - 25))

class Bomba:
    def __init__(self, x, y, tempo_explosao, nivel=1, dono=None):
        self.x = x
        self.y = y
        self.tempo_explosao = tempo_explosao
        self.explodida = False
        self.nivel = nivel
        self.tempo_fogo = 0
        self.fogo = []
        self.dono = dono
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_interval = 0.2

    def atualizar(self, delta_time):
        if not self.explodida:
            self.tempo_explosao -= delta_time
            self.anim_timer += delta_time
            if self.anim_timer >= self.anim_interval:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 3
            if self.tempo_explosao <= 0:
                self.explodir()
        else:
            self.tempo_fogo -= delta_time

    def explodir(self):
        self.explodida = True
        self.tempo_fogo = TEMPO_FOGO
        self.fogo.append((self.x, self.y))
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            for i in range(1 + (self.nivel - 1) * 2):
                nx = self.x + dx * (i + 1)
                ny = self.y + dy * (i + 1)
                if not (0 <= nx < COLS and 0 <= ny < ROWS): break
                if mapa[ny][nx] == 2: break
                self.fogo.append((nx, ny))
                if mapa[ny][nx] == 1: break
        for fx, fy in self.fogo:
            for outra in bombas:
                if not outra.explodida and (outra.x, outra.y) == (fx, fy):
                    outra.explodir()

class Player:
    def __init__(self, x, y, tipo, time, cor_id, ativo=True, ia_fn=None):
        self.grid_x = x
        self.grid_y = y
        self.pixel_x = x * TILE_SIZE
        self.pixel_y = y * TILE_SIZE
        self.dest_x = self.pixel_x
        self.dest_y = self.pixel_y
        self.tipo = tipo
        self.time = time
        
        self.frames = []
        try:
            sprite_sheet = pygame.image.load(f"player{cor_id+1}.png").convert_alpha()
            for i in range(12):
                frame = sprite_sheet.subsurface(pygame.Rect(i * TILE_SIZE, 0, TILE_SIZE, TILE_SIZE))
                self.frames.append(pygame.transform.scale(frame, (TILE_SIZE, TILE_SIZE)))
        except pygame.error:
            # Fallback seguro para testes se a imagem falhar
            pass

        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_interval = 0.15
        self.ultima_direcao = "baixo"

        self.movendo = False
        self.tempo_mov = 0
        self.velocidade = TILE_SIZE / TEMPO_MOVIMENTO
        self.max_bombas = 1
        self.bombas = []
        self.bomba_nivel = 1
        self.ativo = ativo
        self.ia_fn = ia_fn

    def get_acao(self, teclas):
        if vencedor_final is not None or not self.ativo: 
            return "parado"
        if self.tipo == "user":
            return get_acao_usuario(teclas)
        elif self.tipo == "ia" and self.ia_fn:
            self_state = {
                'grid_x': self.grid_x, 'grid_y': self.grid_y,
                'max_bombas': self.max_bombas, 'bombas_ativas': len(self.bombas),
                'bomba_nivel': self.bomba_nivel, 'ativo': self.ativo,
            }
            hud_info = {
                'tile_size': TILE_SIZE, 'rows': ROWS, 'cols': COLS,
                'tempo_movimento': TEMPO_MOVIMENTO, 'tempo_explosao': TEMPO_EXPLOSAO,
                'tempo_fogo': TEMPO_FOGO, 'max_bombas': MAX_BOMBAS,
            }

            chks_player = gerar_checksum_dados(self)
            chks_mapa = gerar_checksum_dados(mapa)
            chks_players = gerar_checksum_dados(players)
            chks_bombas = gerar_checksum_dados(bombas)
            chks_pontos = gerar_checksum_dados(pontos)

            acao = self.ia_fn(self, mapa, players, bombas, tempo_restante, pontos, hud_info, self_state)

            cheat = False
            if gerar_checksum_dados(self) != chks_player: cheat = True
            if gerar_checksum_dados(mapa) != chks_mapa: cheat = True
            if gerar_checksum_dados(players) != chks_players: cheat = True
            if gerar_checksum_dados(bombas) != chks_bombas: cheat = True
            if gerar_checksum_dados(pontos) != chks_pontos: cheat = True

            if cheat:
                for p in players: p.tipo = "cheat"
                self.max_bombas = 10
                return "bomba"
                
            # Trava para não soltar múltiplas bombas do ponto de vista do controlador
            if acao == 'bomba' and self_state['bombas_ativas'] > 0:
                acao = 'parado'
                
            return acao

        return "parado"

    def iniciar_movimento(self, dx, dy):
        self.grid_x += dx
        self.grid_y += dy
        if dy == -1: self.ultima_direcao = "cima"
        elif dy == 1: self.ultima_direcao = "baixo"
        elif dx == -1: self.ultima_direcao = "esquerda"
        elif dx == 1: self.ultima_direcao = "direita"
        self.dest_x = self.grid_x * TILE_SIZE
        self.dest_y = self.grid_y * TILE_SIZE
        self.movendo = True
        self.tempo_mov = 0

    def atualizar(self, delta_time):
        if self.movendo:
            self.tempo_mov += delta_time
            if self.tempo_mov >= TEMPO_MOVIMENTO:
                self.pixel_x = self.dest_x
                self.pixel_y = self.dest_y
                self.movendo = False
                tipo = mapa[self.grid_y][self.grid_x]
                if tipo == 3:
                    if self.max_bombas < MAX_BOMBAS: self.max_bombas += 1
                    mapa[self.grid_y][self.grid_x] = 0
                    pontos[players.index(self)] += PONTOS_POWERUP_COLETADO
                elif tipo == 4:
                    if self.bomba_nivel < 4: self.bomba_nivel += 1
                    mapa[self.grid_y][self.grid_x] = 0
                    pontos[players.index(self)] += PONTOS_POWERUP_COLETADO
            else:
                t = self.tempo_mov / TEMPO_MOVIMENTO
                self.pixel_x = (1 - t) * self.pixel_x + t * self.dest_x
                self.pixel_y = (1 - t) * self.pixel_y + t * self.dest_y

def get_acao_usuario(teclas):
    if teclas[pygame.K_SPACE]: return "bomba"
    elif teclas[pygame.K_UP]: return "cima"
    elif teclas[pygame.K_DOWN]: return "baixo"
    elif teclas[pygame.K_LEFT]: return "esquerda"
    elif teclas[pygame.K_RIGHT]: return "direita"
    return "parado"

def desenhar_mapa():
    for y in range(ROWS):
        for x in range(COLS):
            val = mapa[y][x]
            pygame.draw.rect(screen, COLOR_GRASS, (x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE))
            if val == 0:
                pygame.draw.rect(screen, COLOR_FLOOR, (x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE))
            elif val == 1:
                screen.blit(bloco_img, (x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT))
            elif val == 2:
                pygame.draw.rect(screen, COLOR_INDESTRUCTIBLE, (x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE))
            elif val == 3:
                screen.blit(powerup_bomba_img, (x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT))
            elif val == 4:
                screen.blit(powerup_fogo_img, (x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT))
            pygame.draw.rect(screen, COLOR_BG, (x * TILE_SIZE, y * TILE_SIZE + HUD_HEIGHT, TILE_SIZE, TILE_SIZE), 1)

def desenhar_jogadores(players):
    for p in players:
        if not p.ativo: continue
        if p.movendo:
            p.anim_timer += 1
            if p.anim_timer >= 8:
                p.anim_timer = 0
                p.anim_frame = (p.anim_frame + 1) % 3
        else:
            p.anim_frame = 0

        direcao_idx = {"cima": 0, "direita": 1, "baixo": 2, "esquerda": 3}
        base = direcao_idx.get(p.ultima_direcao, 2) * 3
        
        if p.frames:
            frame = p.frames[base + p.anim_frame]
            screen.blit(frame, (p.pixel_x, p.pixel_y + HUD_HEIGHT))
        else:
            # Fallback
            pygame.draw.rect(screen, (255, 0, 0), (p.pixel_x, p.pixel_y + HUD_HEIGHT, TILE_SIZE, TILE_SIZE))

def desenhar_bombas(bombas):
    for b in bombas:
        if not b.explodida:
            try:
                frame = bomb_frames[b.anim_frame]
                screen.blit(frame, (b.x * TILE_SIZE, b.y * TILE_SIZE + HUD_HEIGHT))
            except NameError:
                pygame.draw.circle(screen, (0,0,0), (int(b.x * TILE_SIZE + TILE_SIZE/2), int(b.y * TILE_SIZE + HUD_HEIGHT + TILE_SIZE/2)), 20)
        else:
            for fx, fy in b.fogo:
                pos_x = fx * TILE_SIZE
                pos_y = fy * TILE_SIZE + HUD_HEIGHT

                try:
                    if (fx, fy) == (b.x, b.y):
                        frame = explosao_frames[1]
                    elif fx == b.x:
                        if fy < b.y:
                            frame = explosao_frames[0] if (fx, fy - 1) not in b.fogo else explosao_frames[3]
                        elif fy > b.y:
                            frame = pygame.transform.rotate(explosao_frames[0], 180) if (fx, fy + 1) not in b.fogo else explosao_frames[3]
                    elif fy == b.y:
                        if fx > b.x:
                            frame = explosao_frames[2] if (fx + 1, fy) not in b.fogo else explosao_frames[4]
                        elif fx < b.x:
                            frame = pygame.transform.flip(explosao_frames[2], True, False) if (fx - 1, fy) not in b.fogo else explosao_frames[4]
                    else:
                        frame = explosao_frames[1]
                    screen.blit(pygame.transform.scale(frame, (TILE_SIZE, TILE_SIZE)), (pos_x, pos_y))
                except NameError:
                    pygame.draw.rect(screen, (255, 100, 0), (pos_x, pos_y, TILE_SIZE, TILE_SIZE))

p1 = "ia_jogador1"
p2 = "ia_jogador2"
p3 = "ia_jogador3"
p4 = "ia_jogador4"
p5 = "ia_jogador1"

ia_mod = importlib.import_module(p1)
ia_1 = getattr(ia_mod, "decidir_acao")

# --- IMPORTAÇÃO DA FUNÇÃO DE RESET DA IA ---
try:
    resetar_episodio = getattr(ia_mod, "resetar_episodio")
except AttributeError:
    # Se não existir ainda no arquivo de IA, criamos uma função provisória (dummy) para evitar crash.
    # O arquivo da IA deve ter o método para zerar estado_anterior e aplicar Game Over.
    def resetar_episodio(morreu=False):
        pass

# --- APRENDIZADO POR CURRÍCULO (SACOS DE PANCADA) ---
def ia_saco_de_pancada(*args):
    return random.choice(["cima", "baixo", "esquerda", "direita", "parado"])

players = [
            Player(0, 0, "ia", 0, 2, ativo=True, ia_fn=ia_1), 
            Player(12, 0, "ia", 1, 0, ativo=True, ia_fn=ia_saco_de_pancada),
            Player(0, 10, "ia", 1, 1, ativo=True, ia_fn=ia_saco_de_pancada),
            Player(12, 10, "ia", 0, 3, ativo=True, ia_fn=ia_saco_de_pancada),
        ]

bombas = []
pontos = [0, 0, 0, 0, 0]
tempo_restante = TEMPO_PARTIDA
vencedor_final = None
mensagem_vitoria = None

clock = pygame.time.Clock()
fullscreen = False
fast_mode = False

ARQUIVO_RELATORIO = "relatorio_treinamento.csv"
episodio_atual = 1

if not os.path.exists(ARQUIVO_RELATORIO):
    with open(ARQUIVO_RELATORIO, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';') 
        writer.writerow(["Episodio", "Vencedor", "Pontos_J1", "Pontos_J2", "Pontos_J3", "Pontos_J4", "Tempo_Decorrido_Segundos"])

partidas_jogadas = 0

while True:
    if fast_mode:
        delta = 1.0 / 60.0  
    else:
        delta = min(clock.tick(60) / 1000.0, 0.1) 

    teclas = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            fullscreen = not fullscreen
            if fullscreen:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            else:
                screen = pygame.display.set_mode((WIDTH, HEIGHT + HUD_HEIGHT))
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F12:
            fast_mode = not fast_mode
            print(f"\n[SISTEMA] Modo de Treinamento Acelerado: {'LIGADO' if fast_mode else 'DESLIGADO'}")

    if vencedor_final is None:
        tempo_restante -= delta
        if tempo_restante <= 0:
            tempo_restante = 0
            vencedor_final = pontos.index(max(pontos))
            nomes = [p1, p2, p3, p4, p5]
            mensagem_vitoria = f"Tempo esgotado! {nomes[vencedor_final]} venceu!"

    for p in players:
        if not p.ativo: continue
        p.atualizar(delta)
        if not p.movendo:
            acao = p.get_acao(teclas)
            dx, dy = 0, 0
            if acao == "cima": dy = -1
            elif acao == "baixo": dy = 1
            elif acao == "esquerda": dx = -1
            elif acao == "direita": dx = 1
            elif acao == "bomba":
                if len(p.bombas) < p.max_bombas:
                    existe_bomba = any(b.x == p.grid_x and b.y == p.grid_y and not b.explodida for b in bombas)
                    if not existe_bomba:
                        nova = Bomba(p.grid_x, p.grid_y, TEMPO_EXPLOSAO, p.bomba_nivel, p)
                        bombas.append(nova)
                        p.bombas.append(nova)
            nx, ny = p.grid_x + dx, p.grid_y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and mapa[ny][nx] in [0, 3, 4]:
                existe_bomba = any(b.x == nx and b.y == ny and not b.explodida for b in bombas)
                bomba_sob_player = any(b.x == p.grid_x and b.y == p.grid_y and not b.explodida for b in p.bombas)
                if not existe_bomba or (nx == p.grid_x and ny == p.grid_y and bomba_sob_player):
                    if (dx != 0 or dy != 0):
                        p.iniciar_movimento(dx, dy)

    if vencedor_final is None:
        for b in bombas[:]:
            b.atualizar(delta)
            if b.explodida and b.tempo_fogo <= 0:
                for fx, fy in b.fogo:
                    if mapa[fy][fx] == 1:
                        mapa[fy][fx] = criar_powerup(fx, fy)
                        if b.dono: pontos[players.index(b.dono)] += PONTOS_BLOCO
                    elif mapa[fy][fx] in [3, 4]:
                        mapa[fy][fx] = 0
                        if b.dono: pontos[players.index(b.dono)] += PONTOS_POWERUP_DESTRUIDO
                bombas.remove(b)
                if b.dono and b in b.dono.bombas:
                    b.dono.bombas.remove(b)

        for b in bombas:
            if b.explodida and b.tempo_fogo > 0:
                for p in players:
                    if p.ativo and (p.grid_x, p.grid_y) in b.fogo:
                        p.ativo = False
                        if b.dono == p:
                            pontos[players.index(p)] -= PONTOS_MATAR_JOGADOR
                            if pontos[players.index(p)]<0: pontos[players.index(p)]=0
                        else:
                            pontos[players.index(b.dono)] += PONTOS_MATAR_JOGADOR

    # --- VERIFICAÇÃO DE FINAL DE JOGO (Com Early Stopping) ---
    if vencedor_final is None:
        if not players[0].ativo:  # A IA principal morreu
            vencedor_final = -2
            mensagem_vitoria = "GAME OVER: A IA principal foi eliminada!"
            # Envia o aviso para a função de IA aplicar penalidade de morte e resetar o estado mental.
            resetar_episodio(morreu=True)
            partidas_jogadas += 1
            
        else:
            vivos = [p for p in players if p.ativo]
            if len(vivos) == 1:
                vencedor_final = players.index(vivos[0])
                pontos[vencedor_final] += PONTOS_VITORIA
                nomes = [p1, p2, p3, p4, p5]
                mensagem_vitoria = f"Jogador {nomes[vencedor_final]} VENCEU!"
                # A IA venceu, reseta para limpar a ação/estado na próxima partida, sem aplicar morte.
                if vencedor_final == 0: 
                    resetar_episodio(morreu=False)
                partidas_jogadas += 1
                
            elif len(vivos) == 0:
                vencedor_final = -1  
                mensagem_vitoria = "EMPATE! Ninguém sobreviveu!"
                partidas_jogadas += 1

    # --- ÚNICO BLOCO DE RENDERIZAÇÃO (Protegido contra gargalo) ---
    if not fast_mode:
        screen.fill(COLOR_BG)
        desenhar_hud(pontos, tempo_restante, partidas_jogadas)
        desenhar_mapa()
        desenhar_bombas(bombas)
        desenhar_jogadores(players)
        if mensagem_vitoria:
            texto = font_vitoria.render(mensagem_vitoria, True, (255, 255, 255))
            rect = texto.get_rect(center=(WIDTH // 2, HEIGHT // 2 + HUD_HEIGHT // 2))
            screen.blit(texto, rect)

        # Alerta Gigante de Treino
        if fast_mode:  # Caso o usuário desligue renderização parcial
            texto_alerta = fonte_grande.render("Modo Treino ativado", True, (255, 50, 50))
            pos_x = (WIDTH // 2) - (texto_alerta.get_width() // 2)
            pos_y = (HEIGHT // 2) - (texto_alerta.get_height() // 2) + HUD_HEIGHT
            screen.blit(texto_alerta, (pos_x, pos_y))

        pygame.display.flip()
    else:
        # Se estiver em Fast Mode, só atualiza o HUD e apaga o resto
        screen.fill(COLOR_BG)
        desenhar_hud(pontos, tempo_restante, partidas_jogadas)
        texto_alerta = fonte_grande.render("Modo Treino Ativado", True, (255, 50, 50))
        pos_x = (WIDTH // 2) - (texto_alerta.get_width() // 2)
        pos_y = (HEIGHT // 2) - (texto_alerta.get_height() // 2) + HUD_HEIGHT
        screen.blit(texto_alerta, (pos_x, pos_y))
        pygame.display.flip()

    # --- RESET DA PARTIDA E TELEMETRIA ---
    if vencedor_final is not None:
        print(mensagem_vitoria)
        
        tempo_decorrido = TEMPO_PARTIDA - tempo_restante
        
        if vencedor_final == -1:
            nome_resultado = "Empate"
        elif vencedor_final == -2:
            nome_resultado = "Derrota (Game Over)"
        else:
            nomes = [p1, p2, p3, p4, p5]
            nome_resultado = f"Jogador {vencedor_final + 1} ({nomes[vencedor_final]})"

        with open(ARQUIVO_RELATORIO, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                episodio_atual, nome_resultado,
                pontos[0], pontos[1], pontos[2], pontos[3],
                round(tempo_decorrido, 2)
            ])
            
        episodio_atual += 1

        # Restaura o mapa original a partir da cópia base
        mapa = [linha[:] for linha in mapa_base]
        
        bombas = []
        pontos = [0, 0, 0, 0, 0]
        tempo_restante = TEMPO_PARTIDA
        vencedor_final = None
        mensagem_vitoria = None
        
        players = [
            Player(0, 0, "ia", 0, 2, ativo=True, ia_fn=ia_1),
            Player(12, 0, "ia", 1, 0, ativo=True, ia_fn=ia_saco_de_pancada),
            Player(0, 10, "ia", 1, 1, ativo=True, ia_fn=ia_saco_de_pancada),
            Player(12, 10, "ia", 0, 3, ativo=True, ia_fn=ia_do_colega),
        ]
        continue