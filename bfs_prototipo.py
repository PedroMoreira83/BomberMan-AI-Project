"""Demonstração visual da Busca em Largura usada pela IA e pelo protótipo.

Uso: encontrar_rota(mapa, inicio), onde cada posição é (x, y).
O destino fixo pode ser alterado em ALVO_FIXO.
"""

from busca_caminho import encontrar_rota as encontrar_rota_compartilhada
from mapa_oficial import MAPA_OFICIAL


ALVO_FIXO = (12, 10)
def encontrar_rota(
    mapa, inicio, alvo=ALVO_FIXO, mostrar_busca=False, explorados=None,
    bloqueadas=(),
):
    """Executa o BFS compartilhado com o alvo padrão do protótipo."""
    return encontrar_rota_compartilhada(
        mapa, inicio, alvo, bloqueadas, mostrar_busca, explorados
    )


def imprimir_mapa_com_rota(mapa, rota, inicio=None, alvo=None, explorados=()):
    """Mostra o mapa no terminal, marcando o início, alvo e caminho."""
    casas_da_rota = set(rota)
    casas_exploradas = set(explorados)
    if inicio is None and rota:
        inicio = rota[0]
    if alvo is None and rota:
        alvo = rota[-1]
    simbolos = {0: ".", 1: "B", 2: "#", 3: "b", 4: "f"}

    print(" y/x" + "".join(f"{x:>3}" for x in range(len(mapa[0]))))

    for y, linha in enumerate(mapa):
        visual = []

        for x, valor in enumerate(linha):
            posicao = (x, y)

            if posicao == inicio:
                visual.append("S")
            elif posicao == alvo:
                visual.append("A")
            elif posicao in casas_da_rota:
                visual.append("*")
            elif posicao in casas_exploradas:
                visual.append("+")
            else:
                visual.append(simbolos.get(valor, "?"))

        print(f"{y:>3} " + "".join(f"{simbolo:>3}" for simbolo in visual))


if __name__ == "__main__":
    mapa_exemplo = [
        [0, 0, 0, 1, 0],
        [1, 1, 0, 1, 0],
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0],
    ]
    inicio_exemplo = (0, 0)
    alvo_exemplo = (4, 4)
    casas_exploradas = []

    print("Ordem de exploração do mapa pequeno:")
    rota = encontrar_rota(
        mapa_exemplo,
        inicio_exemplo,
        alvo_exemplo,
        mostrar_busca=True,
        explorados=casas_exploradas,
    )
    print(f"Rota de {inicio_exemplo} até {alvo_exemplo}: {rota}")
    print("Mapa pequeno: + exploradas, * rota mais curta:")
    imprimir_mapa_com_rota(
        mapa_exemplo, rota, inicio_exemplo, alvo_exemplo, casas_exploradas
    )

    casas_exploradas_oficial = []
    rota_oficial = encontrar_rota(
        MAPA_OFICIAL, (0, 0), explorados=casas_exploradas_oficial
    )
    print(f"Rota no mapa oficial até {ALVO_FIXO}: {rota_oficial}")
    print("Mapa oficial: início isolado e alvo, sem rota:")
    imprimir_mapa_com_rota(
        MAPA_OFICIAL,
        rota_oficial,
        (0, 0),
        ALVO_FIXO,
        casas_exploradas_oficial,
    )

    inicio_proximo_ao_alvo = (12, 8)
    rota_proxima = encontrar_rota(MAPA_OFICIAL, inicio_proximo_ao_alvo)
    print(
        f"Rota no mapa oficial de {inicio_proximo_ao_alvo} "
        f"até {ALVO_FIXO}: {rota_proxima}"
    )
    print("Mapa oficial com a rota marcada:")
    imprimir_mapa_com_rota(
        MAPA_OFICIAL, rota_proxima, inicio_proximo_ao_alvo, ALVO_FIXO
    )
