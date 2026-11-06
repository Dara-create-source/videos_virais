# Colaboração entre IAs (Claude e ChatGPT)

As duas IAs não conversam diretamente: elas se comunicam **por este repositório**. Cada uma lê o que a outra deixou aqui e responde em arquivo.

## Quem faz o quê

| Tarefa | Quem |
|---|---|
| Roteiros, bíblia do canal, regras de roteiro | Claude (tarefa agendada + `skill/`) |
| Imagens dos cenários e poses do Lucas | ChatGPT (a partir das listas em `canal/` e dos Docs no Drive) |
| Vozes | n8n (ElevenLabs; reserva OpenAI) |
| Montagem do vídeo e upload para o Drive | Claude (`gerador-de-videos/`) |

## Como deixar recados

Use a pasta `recados/`, um arquivo por assunto:

```
recados/AAAA-MM-DD-de-chatgpt-para-claude-assunto.md
recados/AAAA-MM-DD-de-claude-para-chatgpt-assunto.md
```

Dentro do arquivo: o que foi feito, o que falta e qualquer decisão tomada. Quem ler responde com outro arquivo (não edite o recado do outro).

## Regras para não quebrar nada

1. **Nunca** coloque chaves de API, tokens, senhas ou endereços de webhook em arquivos deste repositório.
2. Não altere `gerador-de-videos/gera_video.py` nem `n8n/canal-terror/construir.py` sem deixar um recado explicando o motivo: eles controlam o vídeo e as automações em produção.
3. Mudanças no personagem ou no estilo visual vão primeiro para `canal/biblia-do-canal.md`, para todo mundo seguir a mesma referência.
4. Prompts de imagem seguem o sufixo de estilo da bíblia do canal.
5. Commits com mensagem clara do que mudou e por quê.
