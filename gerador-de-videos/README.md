# Gerador de vídeos narrados

Transforma um roteiro em JSON + imagens em um vídeo pronto para TikTok, Shorts ou YouTube:
narração com voz em português, legendas grandes, zoom, tremor, luz piscando, personagem
por cima do cenário, efeitos sonoros e clima de fundo.

## Preparar (uma vez)

```bash
./baixar_voz.sh
```

Precisa de Python 3 com Pillow e numpy, e do ffmpeg.

## Gerar um vídeo

```bash
python3 gera_video.py exemplo-dia1/roteiro.json
```

`--rapido` gera uma prévia pequena em segundos. `-o arquivo.mp4` escolhe o nome da saída.

Para testar sem as artes de verdade: `python3 exemplo-dia1/gerar_placeholders.py`.

## Formato do roteiro

```json
{
  "config": {
    "formato": "9:16",              // ou "16:9" (YouTube longo) ou "1:1"
    "modelo_voz": "../vozes/pt_BR-faber-medium.onnx",
    "velocidade_voz": 1.15,         // maior = mais devagar
    "pausa": 0.9,                   // duração de cada [pausa]
    "palavras_legenda": 3,
    "contador": {"valor": "DIA 1"}, // caixinha fixa no canto (opcional)
    "musica": "musica.mp3",         // opcional
    "volume_musica": 0.12,
    "chamada": "serie",             // "serie" ou "avulso": curtir e seguir automático
    "chamada_personagem": "imagens/lucas_lanterna.png",
    "chamada_meio": 0.45            // onde a faixa do meio aparece (fração do vídeo)
  },
  "cenas": [
    {
      "narracao": "Texto da legenda. Use [pausa] para silêncio.",
      "fala": "Texto falado, se for diferente da legenda (opcional)",
      "audio": "minha_voz_cena1.mp3",     // sua gravação no lugar da voz automática (opcional)
      "fundo": "imagens/posto.png",
      "fundo_depois": "imagens/posto_apagado.png", "troca_em": 2.5,
      "personagem": "imagens/lucas_medo.png",     // fundo branco é removido sozinho
      "personagem_depois": "imagens/lucas_lanterna.png", "troca_personagem_em": 7,
      "posicao": "centro",            // esquerda | centro | direita
      "tamanho": 0.42,                // altura do personagem (fração da tela)
      "chao": 0.80,                   // onde ficam os pés (fração da tela)
      "personagem_efeito": "tremer",  // tremer | entrar
      "efeito": "zoom_lento",         // zoom_lento | zoom_rapido | afastar | tremor | piscar | nenhum
      "texto_tela": "20%", "texto_tela_cor": [235, 60, 60], "texto_piscando": true,
      "sons": ["impacto", {"som": "bip", "em": 0.6, "volume": 0.8}, {"som": "passos.mp3", "em": 1}],
      "final_preto": true,
      "pausa_depois": 0.25
    }
  ]
}
```

Sons já incluídos (gerados por código): `impacto`, `bip`, `chiado`, `batida`, `estalo`.
Qualquer arquivo `.mp3`/`.wav` também funciona.

Números como `3h17` e `20%` são lidos por extenso automaticamente.

## Chamada para curtir e seguir

Com `"chamada"` na config, todo vídeo ganha:
1. uma faixa animada no topo, no meio do vídeo ("CURTE E SEGUE PRO PRÓXIMO DIA" ou "…PRA MAIS HISTÓRIAS");
2. uma cena final depois do corte para o preto, com a voz pedindo para curtir e seguir e os botões CURTIR e SEGUIR na tela.

Os áudios ficam em `chamadas/` e são gravados uma vez só (`serie.mp3`, `avulso.mp3`). Para trocar a frase da faixa, use `"chamada_texto"`.

## Salvar direto no Drive

`python3 gera_video.py projeto/roteiro.json --drive` gera o vídeo e já envia o MP4 para a pasta
**Videos virais** do Google Drive. Para enviar um vídeo que já existe: `python3 enviar_drive.py video.mp4`.
O envio passa pelo workflow "Canal Terror · 5 · Iniciar upload de vídeo" do n8n (endereço em
`../n8n/canal-terror/workflows_publicados.json`, que fica fora do git).
