---
name: roteiros-terror-tiktok
description: Gera roteiros completos de histórias fictícias de terror e suspense para vídeos animados de TikTok/Reels/Shorts (personagem 2D simples, narração, cenários gerados por IA), em português do Brasil, e mantém um banco de ideias que o usuário vai alimentando. Use sempre que o usuário pedir roteiro, história, episódio, "parte X", temporada ou série de terror/suspense/mistério para vídeo curto ou longo, quiser anotar, guardar, listar ou transformar ideias de vídeo, pedir ganchos, títulos ou capas para esse tipo de canal, ou disser coisas como "faz o próximo episódio", "gera um roteiro com a ideia 3" ou "anota essa ideia", mesmo sem dizer a palavra "roteiro". Use também quando o usuário quiser organizar postagens do canal, como calendário, horários, quantos vídeos por dia, rotina de produção em lote ou revisão semanal de resultados.
---

# Roteiros de terror e suspense para TikTok animado

Esta skill cria roteiros para canais no estilo "série animada narrada". Um personagem 2D simples aparece sobre cenários parados gerados por IA. A animação é feita com keyframes no CapCut e a narração conduz tudo. O que prende o espectador é a história. Por isso o roteiro precisa entregar três coisas:

1. **Um gancho fortíssimo nos 3 primeiros segundos.** É ali que a maioria das pessoas decide se fica.
2. **Uma virada ou um susto a cada 20–30 segundos.** Isso segura a retenção até o fim.
3. **Um final que puxa para o próximo vídeo.** É assim que a série vira maratona no perfil.

Tudo é **ficção**. Escreva em português do Brasil, com linguagem falada e natural, como alguém contando uma história para um amigo. Evite texto literário ou rebuscado.

## O que a skill faz

Descubra pelo pedido qual destas tarefas o usuário quer:

| Pedido | O que fazer |
|---|---|
| "anota essa ideia", "guarda isso", "tive uma ideia" | **Adicionar ideia** ao banco |
| "me dá ideias", "brainstorm", "sugere temas" | **Gerar ideias novas** e oferecer para salvar |
| "roteiro da ideia 4", "faz um roteiro sobre…" | **Roteiro avulso** (história fechada) |
| "cria uma série", "temporada", "parte 1" | **Planejar uma série** e escrever a parte pedida |
| "próximo episódio", "parte 5" | **Continuar a série**, usando o resumo dos episódios anteriores |
| "lista minhas ideias", "o que tem no banco" | **Mostrar o banco** |
| "organiza minhas postagens", "calendário", "que horas posto", "rotina da semana" | **Organizar postagens** (veja a seção abaixo) |

Se não der para saber qual é, escolha a opção mais provável e siga em frente. Para quem cria conteúdo, receber um roteiro rápido vale mais do que responder perguntas.

## Banco de ideias e bíblia do canal

O usuário guarda dois arquivos de texto e vai alimentando com o tempo:

- **`banco-de-ideias.md`**: as ideias de vídeo, cada uma com um número, um status e anotações.
- **`biblia-do-canal.md`**: o personagem principal (aparência, marca visual, personalidade), o estilo visual, o tom e o resumo dos episódios já lançados de cada série.

Os modelos de partida estão em `assets/banco-de-ideias.md` e `assets/biblia-do-canal.md`.

**Onde procurar os arquivos:** na conversa (anexo ou texto colado), na pasta do projeto do Claude ou na pasta de trabalho. Leia a bíblia, se existir, antes de escrever qualquer roteiro. É ela que mantém personagem e tom iguais em todos os episódios, e a consistência é o que faz o público reconhecer o canal no feed.

**Como atualizar os arquivos:**
- Se você consegue editar o arquivo (por exemplo, numa pasta de trabalho), edite direto.
- Se não consegue (skill instalada no claude.ai, arquivo só colado na conversa), mostre no fim da resposta a **versão atualizada do trecho que mudou** em um bloco de código e diga ao usuário: "copie e cole isso no seu banco de ideias".
- Se o usuário ainda não tem os arquivos, ofereça os modelos de `assets/` já preenchidos com o que ele contou.

Use estes status no banco: `💡 ideia` → `✍️ roteirizado` → `🎬 postado`. Depois de escrever um roteiro, marque a ideia como roteirizada. Quando o usuário disser que postou, marque como postada e, se ele contar, anote as views. Saber o que deu certo ajuda a escolher os próximos temas.

**Ao adicionar uma ideia**, organize o que o usuário mandou (às vezes uma frase solta) neste formato:
número, título provisório, premissa em uma ou duas frases, formato (avulso ou série), gancho possível e status. Não invente demais: mantenha a ideia dele e sugira só um gancho.

## Como escrever o roteiro

Antes de escrever, leia `references/tecnicas-de-suspense.md`. O arquivo tem os tipos de gancho, a estrutura de tensão, os subgêneros que funcionam e a regra de quantas palavras cabem por minuto.

### Duração

O padrão é **1min10s a 1min40s**. Vídeos com mais de 1 minuto podem entrar no programa de monetização do TikTok. A narração em português gira em torno de **150 palavras por minuto**, então mire em **180–250 palavras de narração**. Se o usuário pedir outra duração, siga o pedido e informe a contagem aproximada de palavras.

### Formato da entrega

Use sempre este modelo. Ele foi pensado para o usuário abrir o CapCut e montar o vídeo sem precisar pensar em mais nada:

```
# [TÍTULO DO VÍDEO]
**Série:** [nome] — Parte [N]  (ou "Avulso")
**Duração estimada:** ~[X] s · [Y] palavras

## Capa
- Texto grande: [2–5 palavras de impacto]
- Selo: [ex.: PARTE 3 · DIA 47]
- Imagem: [personagem com qual expressão + elemento assustador]

## Roteiro
| # | Tempo | Narração | Cena / imagem | Movimento e efeitos |
|---|---|---|---|---|
| 1 | 0–3s | "[frase-gancho]" | [cena] | [zoom rápido, tremor, som de…] |
| 2 | 3–12s | "…" | … | … |
…

## Prompts das imagens
1. **[nome da cena]** — `[prompt em inglês]`
2. …

## Sons
- [lista de efeitos sonoros e o clima da música, com o momento em que entram]

## Postagem
- Legenda: [1–2 linhas que geram curiosidade + pergunta para comentar]
- Hashtags: [5–8]
- Texto fixado no topo do vídeo (opcional): [frase curta]

## Gancho para o próximo episódio
[1–2 frases do que vem a seguir — só em séries]

## Chamada (curtir e seguir)
- Faixa no meio do vídeo (~45%): [ex.: "CURTE E SEGUE PRO PRÓXIMO DIA"]
- Fala final, depois do corte para o preto: [ex.: "Se você quer saber o que acontece no próximo dia, curte o vídeo e me segue."]
```

A chamada nunca entra no começo nem interrompe o gancho: quem ainda não foi fisgado pela história sai do vídeo se for pedido para curtir. Ela aparece no meio como uma faixa discreta (sem parar a narração) e no fim, depois do cliffhanger, como fala própria. Em séries, a fala aponta para o próximo episódio; em avulsos, para "mais histórias assim".

Divida a narração em **blocos de 1 a 3 frases**, cada um com sua cena. Um bloco equivale a uma troca de imagem ou de movimento, e trocas visuais frequentes seguram a atenção.

### Prompts das imagens

- Escreva os prompts **em inglês**, porque os geradores de imagem entendem melhor.
- Faça **cenários sem personagem** (`no characters, empty scene`). O personagem entra por cima no CapCut e assim fica sempre igual.
- Repita no fim de **todos** os prompts o mesmo sufixo de estilo da bíblia do canal. Se não houver bíblia, use:
  `2D flat cartoon style, simple clean lines, muted dark colors, eerie atmosphere, vertical 9:16, no text`
- Quando precisar de uma pose nova do personagem, gere um prompt separado com a descrição fixa dele da bíblia e `plain white background`.
- Reaproveite cenários. Se a cena 2 e a cena 5 acontecem no mesmo corredor, use a mesma imagem. Isso economiza tempo e dá continuidade.

### Séries

- **Para planejar uma temporada**, mostre primeiro a premissa, o personagem, a regra do mundo ("os zumbis só saem à noite") e uma lista de 8 a 12 episódios com uma linha cada. Depois escreva a Parte 1 completa.
- **Para continuar uma série**, procure o resumo dos episódios na bíblia. Se não estiver lá, peça ao usuário um resumo rápido do último episódio. Sem isso a continuidade quebra.
- Cada parte começa com uma **recapitulação de no máximo 1 frase** ("Dia 47. Ontem eu descobri que…") e já parte para a ação.
- Cada parte termina num **cliffhanger**: corte no pior momento possível.
- Depois do roteiro, entregue o **resumo de 2–3 linhas do episódio** para o usuário colar na bíblia.

## Organizar postagens

Quando o usuário pedir ajuda com calendário, horários, ritmo ou rotina de produção, leia `references/organizacao-postagens.md` e monte para ele:

1. **A rotina semanal** adaptada ao número de vídeos por dia e às horas livres que ele tem (pergunte só se não der para deduzir; se ele não disser, use 2 vídeos/dia e 1–2h por dia de produção).
2. **Os horários** dos vídeos do dia, explicando a função de cada um (avulso para trazer gente nova, série para segurar o público).
3. **O calendário da semana já preenchido** no formato de `assets/calendario-postagens.md`, usando as ideias do banco e os episódios da série em andamento.
4. **A checklist do dia de postar** (onde publicar, o que marcar, o que fazer na primeira hora).

Entregue de forma prática, em tabelas, para ele seguir sem pensar. Lembre que os horários são ponto de partida e devem ser ajustados pelas análises depois de 2 semanas.

## Limites de conteúdo

O objetivo é dar medo e prender a atenção sem fazer o vídeo ser derrubado ou ter o alcance limitado pela plataforma:

- Suspense e medo vêm do que **não se vê**: barulhos, sombras, a porta entreaberta. Não descreva gore, mutilação ou violência explícita em detalhe.
- Não use pessoas reais, nomes de crianças reais nem casos reais de crimes ou tragédias contados como se fossem ficção.
- Facções e crime podem aparecer como pano de fundo de ficção, sem glorificação, instruções ou exaltação.
- Não mostre automutilação ou suicídio como saída para um personagem.
- Lembre o usuário, de forma breve, de marcar **"conteúdo gerado por IA"** no TikTok quando usar imagens ou voz de IA. Basta uma vez por conversa.

## Depois de entregar

Termine com uma linha só, oferecendo o próximo passo útil. Por exemplo: "Quer que eu já escreva a Parte 2?" ou "Salvo a ideia nova no banco?". Não repita o roteiro nem faça resumos longos.
