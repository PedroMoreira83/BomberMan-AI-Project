"""Mapa oficial compartilhado pelo jogo e pelo protótipo de BFS."""

MAPA_OFICIAL = [
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

ALTURA_MAPA = len(MAPA_OFICIAL)
LARGURA_MAPA = len(MAPA_OFICIAL[0]) if MAPA_OFICIAL else 0

# Valores usados pelo jogo: chão, bloco destrutível, parede e power-ups.
CHAO = 0
BLOCO = 1
PAREDE = 2
POWERUP_BOMBA = 3
POWERUP_FOGO = 4

# Uma casa só é caminho livre se o jogador pode entrar nela agora.
TERRENOS_LIVRES = frozenset({CHAO, POWERUP_BOMBA, POWERUP_FOGO})


def coordenada_no_mapa(mapa, x, y):
    """Informa se a coordenada existe, mesmo em mapas não retangulares."""
    return 0 <= y < len(mapa) and 0 <= x < len(mapa[y])


def celula_caminhavel(mapa, x, y):
    """Informa se (x, y) está dentro do mapa e pode ser atravessada."""
    return coordenada_no_mapa(mapa, x, y) and mapa[y][x] in TERRENOS_LIVRES
