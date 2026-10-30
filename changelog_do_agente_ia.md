# Documentação de Evolução do Agente IA (Q-Learning)

Este documento registra as principais atualizações, correções de comportamento e ajustes de recompensa aplicados na lógica de aprendizado por reforço do nosso agente, desde a implementação do sistema de aglutinação de memórias.

## 🛠️ Evolução da Lógica de Recompensas e Movimentação (Pós-Aglutinador)

Para garantir um comportamento mais agressivo e inteligente por parte da IA, implementamos as seguintes melhorias em nosso código principal:

*   **Ajuste no Aglutinador (Remoção do Efeito Catraca):** 
    O script aglutinador original apenas sobreescrevia os dados mantendo o valor máximo absoluto. Isso impedia o agente de desaprender ações ruins que já haviam pontuado muito alto. A lógica foi alterada para utilizar uma **média ponderada** entre o conhecimento antigo e o novo, permitindo que o modelo se adapte e corrija valores superestimados naturalmente.
*   **Fim do *Farm* de Fuga (Bombas Inócuas):** 
    O modelo havia descoberto uma falha no sistema de recompensas onde plantar uma bomba inútil longe de tudo e fugir gerava lucro infinito. A pontuação de fuga foi reduzida drasticamente. A ação de plantar bomba agora só recebe validação positiva se houver um tijolo destrutível ou um inimigo dentro do raio real da explosão (calculado em formato de cruz).
*   **Implementação da *Step Penalty* (Fim da Dança Infinita):** 
    Para *farmar* a recompensa de aproximação do alvo, o bot começou a dar um passo para frente e um para trás indefinidamente. A recompensa positiva por caminhar foi removida e substituída por uma **punição contínua de inércia** (`-2` pontos por frame sem interações úteis). Isso obriga o bot a agir rapidamente em direção aos objetivos.
*   **Visão de *Power-ups* no Farol Global:** 
    O algoritmo de busca de rotas (Dijkstra) não enxergava os itens do jogo. Os blocos de *power-up* foram adicionados como alvos válidos na matriz de navegação, fazendo o bot explorar ativamente o mapa para buscar melhorias de fogo e aumento da capacidade de bombas.
*   **Correção do *Raycast* ("Cegueira de Parede"):** 
    Corrigimos um *bug* no laço de repetição que simulava o alcance das bombas. Anteriormente, se o raio da explosão encostasse em uma quina de parede de ferro indestrutível, o código interrompia toda a verificação, impedindo o bot de enxergar alvos válidos nas outras direções.
*   **Otimização de Gargalo de I/O (Desempenho):** 
    A frequência de salvamento no disco (`q_table_j1.json`) foi expandida para ocorrer apenas a cada 15.000 passos, evitando o travamento da *engine* e a queda drástica de FPS na máquina durante longas sessões de treinamento.

## 🧹 A Necessidade de Intervenção com o `higienizar_json.py`

Mesmo após aplicarmos todas as correções lógicas acima no código Python, notamos que o bot continuava agindo de forma passiva. Isso ocorreu porque a memória (Q-Table) havia sido gravemente contaminada pelas falhas de recompensa das gerações anteriores, herdando estados onde ações incorretas (como plantar bombas no vazio) valiam milhares de pontos.

O script `higienizar_json.py` foi desenvolvido como uma **intervenção cirúrgica de uso único**. Ele não faz parte da rotina de execução padrão do bot. 

**Motivo do uso:** Precisávamos varrer o arquivo JSON e "desinflar" forçadamente esses valores absurdos, trazendo o teto de pontuação de ações erradas para a nova realidade negativa. Essa higienização salvou a nossa base de dados: conseguimos desintoxicar a Q-Table sem jogar fora o valioso mapeamento estrutural de quase 10.000 estados já explorados, permitindo que o bot assimilasse as novas regras imediatamente.