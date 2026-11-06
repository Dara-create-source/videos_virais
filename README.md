# Vídeos Virais — Canal Terror

Tudo o que faz o canal de histórias de terror e suspense animadas (TikTok, YouTube Shorts e Reels) funcionar: roteiros, personagem, gerador de vídeo e automações.

## Como o canal funciona

```
6h35  Tarefa agendada do Claude escreve 3 roteiros (1 avulso + história parte 1 e 2)
        └─ n8n salva em Google Docs, registra na planilha e avisa no WhatsApp
Dono   responde no WhatsApp: "aprovo 1 3" / "refaz 2: ..."
        └─ n8n gera as vozes de cada cena (ElevenLabs; reserva: OpenAI) e salva no Drive
Dono   gera as imagens no ChatGPT e manda
Claude monta o vídeo (gerador-de-videos) e salva o MP4 em "Videos virais" no Drive
```

## Pastas

| Pasta | O que tem |
|---|---|
| `canal/` | Bíblia do canal (Lucas, estilo, séries), temporada do APAGÃO, roteiros e listas de prompts de imagem |
| `skill/` | Skill "roteiros-terror-tiktok" (regras de roteiro, banco de ideias, organização de postagens). O `.skill` instala no Claude |
| `gerador-de-videos/` | `gera_video.py`: roteiro em JSON + imagens + áudios → MP4 vertical com legendas, efeitos, sons e chamada "curte e segue". `enviar_drive.py` sobe o vídeo para o Drive. Cada pasta de projeto (`bomba-4/`, `apagao-dia2/`...) tem o `roteiro.json` de um vídeo |
| `n8n/canal-terror/` | `construir.py` cria/atualiza os workflows no n8n; `prompt_sistema.md` são as regras que o roteirista segue |

## O que fica fora do Git (de propósito)

- Endereços secretos dos webhooks e configuração local (`n8n/canal-terror/config.json`, `workflows_publicados.json`). Use `config.exemplo.json` como modelo.
- Chaves de API: ficam só nas credenciais do n8n ou nos segredos do ambiente, nunca em arquivo.
- Imagens, áudios e vídeos (ficam no Google Drive, pasta "Videos virais") e o modelo de voz offline (`gerador-de-videos/baixar_voz.sh` baixa).

## Trabalho com mais de uma IA

Este repositório é usado pelo Claude e pelo ChatGPT. Veja `COLABORACAO.md` para combinar quem faz o quê sem um atrapalhar o outro.
