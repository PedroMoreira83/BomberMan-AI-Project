"""Busca em Largura compartilhada pelo protótipo e pela IA do jogo."""

from collections import deque

from mapa_oficial import celula_caminhavel


DIRECOES = ((0, -1), (0, 1), (-1, 0), (1, 0))


def calcular_distancias_mapa(mapa, origens, bloqueadas=()):
    """Retorna a distância em passos desde as origens até cada casa alcançável."""
    bloqueadas = set(bloqueadas)
    distancias = {
        origem: 0
        for origem in origens
        if celula_caminhavel(mapa, *origem) and origem not in bloqueadas
    }
    fila = deque(distancias)

    while fila:
        x, y = fila.popleft()
        for dx, dy in DIRECOES:
            vizinho = (x + dx, y + dy)
            if (
                celula_caminhavel(mapa, *vizinho)
                and vizinho not in bloqueadas
                and vizinho not in distancias
            ):
                distancias[vizinho] = distancias[(x, y)] + 1
                fila.append(vizinho)

    return distancias


def encontrar_rota(
    mapa, inicio, alvo, bloqueadas=(), mostrar_busca=False, explorados=None
):
    """Retorna a menor rota entre início e alvo como lista de (x, y).

    Casas fora do mapa, paredes, blocos e posições em ``bloqueadas`` não são
    atravessadas. Retorna uma lista vazia quando não há rota.
    """
    if not mapa or not mapa[0]:
        return []

    largura = len(mapa[0])
    if any(len(linha) != largura for linha in mapa):
        raise ValueError("O mapa precisa ser retangular.")

    bloqueadas = set(bloqueadas)

    def caminhavel(posicao):
        x, y = posicao
        return celula_caminhavel(mapa, x, y) and posicao not in bloqueadas

    if not caminhavel(inicio) or not caminhavel(alvo):
        return []

    if explorados is not None:
        explorados.clear()

    fila = deque([inicio])
    anterior = {inicio: None}
    visitados = []

    while fila:
        atual = fila.popleft()
        visitados.append(atual)
        if mostrar_busca:
            print(f"Explorando {atual}")
        if atual == alvo:
            break

        x, y = atual
        for dx, dy in DIRECOES:
            vizinho = (x + dx, y + dy)
            if caminhavel(vizinho) and vizinho not in anterior:
                anterior[vizinho] = atual
                fila.append(vizinho)

    if explorados is not None:
        explorados.extend(visitados)

    if alvo not in anterior:
        return []

    rota = []
    atual = alvo
    while atual is not None:
        rota.append(atual)
        atual = anterior[atual]
    rota.reverse()
    return rota
