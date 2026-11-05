"""Controlador-base de inimigos com movimento aleatório no mapa do jogo."""

import random
from mapa_oficial import celula_caminhavel


class InimigoAleatorio:
    """Escolhe aleatoriamente uma casa vizinha sem atravessar paredes.

    A colisão com bombas, jogadores e os demais elementos continua sob
    responsabilidade do motor do jogo. O controlador valida somente o mapa.
    """

    ACOES_DIRECIONAIS = (
        ("cima", 0, -1),
        ("baixo", 0, 1),
        ("esquerda", -1, 0),
        ("direita", 1, 0),
    )

    def decidir_acao(
        self, player, mapa, jogadores, bombas, tempo_restante, pontos,
        hud_info, self_state
    ):
        x = self_state["grid_x"]
        y = self_state["grid_y"]
        movimentos_validos = []
        for acao, dx, dy in self.ACOES_DIRECIONAIS:
            nx, ny = x + dx, y + dy
            if celula_caminhavel(mapa, nx, ny):
                movimentos_validos.append(acao)

        return random.choice(movimentos_validos) if movimentos_validos else "parado"

    __call__ = decidir_acao
