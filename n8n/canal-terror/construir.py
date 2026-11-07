#!/usr/bin/env python3
"""Cria/atualiza no n8n os workflows do Canal Terror.

Quem escreve os roteiros é uma TAREFA AGENDADA do Claude (aba Agendados). O n8n cuida de
Drive, planilha e WhatsApp:

  1 · Contexto            GET  /webhook/canal-terror-contexto-<sufixo>
                           → títulos já usados, se hoje já tem roteiros, pedidos de "refaz" pendentes
  2 · Receber roteiros    POST /webhook/canal-terror-roteiros-<sufixo>
                           → cria os Google Docs, registra na planilha, avisa no WhatsApp
  3 · Receber revisão     POST /webhook/canal-terror-revisao-<sufixo>
                           → cria a nova versão do Doc, atualiza a linha, avisa no WhatsApp
  4 · Aprovação WhatsApp  POST /webhook/canal-terror-whatsapp-<sufixo>  (webhook da Evolution)
                           → "aprovo 1 2 3" marca aprovado; "refaz 2: ..." marca para reescrever

Uso: python3 construir.py [--so-json] [--ativar]
A chave do n8n é injetada pelo proxy desta sessão; nada de segredo fica no código.
"""
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
N8N = "https://editor.marketflowpartners.com.br"
IDS = json.loads((AQUI / "ids.json").read_text(encoding="utf-8"))
CRED = IDS["credenciais"]
CFG = json.loads((AQUI / "config.json").read_text(encoding="utf-8"))
SUF = CFG["sufixo_webhook"]
VOZ = {"voice_id": "bIHbv24MWmeRgasZH58o", "model_id": "eleven_multilingual_v2",
       "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.1, "speed": 0.95}}


def credencial_por_nome(nome, tipo):
    out = subprocess.run(["curl", "-sS", "--max-time", "30", f"{N8N}/api/v1/credentials"], capture_output=True, text=True).stdout
    try:
        for c in json.loads(out).get("data", []):
            if c["type"] == tipo and c["name"].strip().lower() == nome.lower():
                return {"id": c["id"], "name": c["name"]}
    except Exception:
        pass
    return None


ELEVEN = credencial_por_nome("ElevenLabs", "httpHeaderAuth")
TIPOS_VALIDOS = "['avulso','parte1','parte2']"


def js(s) -> str:
    return json.dumps(s, ensure_ascii=False)


def node(nome, tipo, versao, params, pos, cred=None, **extra):
    n = {"parameters": params, "name": nome, "type": tipo, "typeVersion": versao, "position": pos}
    if cred:
        n["credentials"] = cred
    n.update(extra)
    return n


def ligar(wf, *nomes):
    for a, b in zip(nomes, nomes[1:]):
        wf["connections"].setdefault(a, {"main": [[]]})["main"][0].append({"node": b, "type": "main", "index": 0})


def novo_wf(nome):
    return {"name": nome, "nodes": [], "connections": {},
            "settings": {"executionOrder": "v1", "timezone": "America/Sao_Paulo"}}


CONFIG_JS = f"""
const data = new Date().toLocaleDateString('sv-SE', {{ timeZone: 'America/Sao_Paulo' }});
return [{{ json: {{
  data_post: data,
  pasta_id: {js(IDS['pasta_drive_id'])},
  planilha_id: {js(IDS['planilha_id'])},
  whatsapp_numero: {js(CFG.get('whatsapp_numero', ''))},
  whatsapp_instancia: {js(CFG.get('whatsapp_instancia', ''))},
}} }}];
"""


def webhook(nome, caminho, metodo="POST", resposta="lastNode", pos=(0, 100)):
    p = f"canal-terror-{caminho}-{SUF}"
    return node(nome, "n8n-nodes-base.webhook", 2,
                {"httpMethod": metodo, "path": p, "responseMode": resposta, "options": {}}, list(pos), webhookId=p)


def code(nome, src, pos, **extra):
    return node(nome, "n8n-nodes-base.code", 2, {"jsCode": src}, pos, **extra)


def sheets_read(nome, pos):
    return node(nome, "n8n-nodes-base.googleSheets", 4.5, {
        "documentId": {"__rl": True, "value": "={{ $('Config').first().json.planilha_id }}", "mode": "id"},
        "sheetName": {"__rl": True, "value": "roteiros", "mode": "name"},
        "options": {},
    }, pos, {"googleSheetsOAuth2Api": CRED["googleSheetsOAuth2Api"]}, alwaysOutputData=True)


def sheets_append(nome, pos):
    return node(nome, "n8n-nodes-base.googleSheets", 4.5, {
        "operation": "append",
        "documentId": {"__rl": True, "value": "={{ $('Config').first().json.planilha_id }}", "mode": "id"},
        "sheetName": {"__rl": True, "value": "roteiros", "mode": "name"},
        "columns": {"mappingMode": "autoMapInputData", "value": {}},
        "options": {},
    }, pos, {"googleSheetsOAuth2Api": CRED["googleSheetsOAuth2Api"]})


def sheets_update(nome, pos):
    return node(nome, "n8n-nodes-base.googleSheets", 4.5, {
        "operation": "update",
        "documentId": {"__rl": True, "value": "={{ $('Config').first().json.planilha_id }}", "mode": "id"},
        "sheetName": {"__rl": True, "value": "roteiros", "mode": "name"},
        "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": ["row_number"]},
        "options": {},
    }, pos, {"googleSheetsOAuth2Api": CRED["googleSheetsOAuth2Api"]})


def docs_criar(nome, titulo_expr, pos):
    return node(nome, "n8n-nodes-base.googleDocs", 2, {
        "folderId": "={{ $('Config').first().json.pasta_id }}",
        "title": titulo_expr,
    }, pos, {"googleDocsOAuth2Api": CRED["googleDocsOAuth2Api"]})


def docs_escrever(nome, texto_expr, pos):
    return node(nome, "n8n-nodes-base.googleDocs", 2, {
        "operation": "update",
        "documentURL": "={{ $json.id }}",
        "actionsUi": {"actionFields": [{"action": "insert", "text": texto_expr}]},
    }, pos, {"googleDocsOAuth2Api": CRED["googleDocsOAuth2Api"]})


def tem_whatsapp(nome, pos):
    return node(nome, "n8n-nodes-base.if", 2, {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
            "conditions": [{"id": "wa", "leftValue": "={{ $json.numero }}", "rightValue": "",
                            "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}],
            "combinator": "and",
        },
        "options": {},
    }, pos)


def whatsapp(nome, pos):
    return node(nome, "n8n-nodes-evolution-api.evolutionApi", 1, {
        "resource": "messages-api",
        "instanceName": "={{ $json.instancia }}",
        "remoteJid": "={{ $json.numero }}",
        "messageText": "={{ $json.texto }}",
        "options_message": {},
    }, pos, {"evolutionApi": CRED["evolutionApi"]})


# --------------------------------------------------------------------------- #
def wf_contexto():
    wf = novo_wf("Canal Terror · 1 · Contexto")
    N = wf["nodes"]
    N.append(webhook("Pedido", "contexto", metodo="GET"))
    N.append(code("Config", CONFIG_JS, [220, 100]))
    N.append(sheets_read("Ler planilha", [440, 100]))
    N.append(code("Separar", f"""
const cfg = $('Config').first().json;
const linhas = $input.all().map(i => i.json).filter(r => {TIPOS_VALIDOS}.includes(r.tipo));
const refazer = linhas.filter(r => r.status === 'refazer');
const saida = {{
  hoje: cfg.data_post,
  ja_tem_hoje: linhas.some(r => String(r.data_post) === cfg.data_post),
  titulos_usados: linhas.slice(-90).map(r => r.titulo),
  refazer: refazer.map(r => ({{ row_number: r.row_number, data_post: r.data_post, numero: r.numero, tipo: r.tipo,
    titulo: r.titulo, versao: r.versao, feedback: r.feedback, doc_id: r.doc_id }})),
}};
return [{{ json: saida }}];
""", [660, 100]))
    N.append(node("Tem refazer?", "n8n-nodes-base.if", 2, {
        "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                       "conditions": [{"id": "rf", "leftValue": "={{ $json.refazer.length }}", "rightValue": 0,
                                       "operator": {"type": "number", "operation": "gt"}}],
                       "combinator": "and"}, "options": {}}, [880, 100]))
    N.append(code("Um por item", "return $input.first().json.refazer.map(r => ({ json: r }));", [1100, 0]))
    N.append(node("Ler roteiro atual", "n8n-nodes-base.googleDocs", 2, {
        "operation": "get", "documentURL": "={{ $json.doc_id }}", "simple": True},
        [1320, 0], {"googleDocsOAuth2Api": CRED["googleDocsOAuth2Api"]}))
    N.append(code("Juntar", """
const base = $('Separar').first().json;
const docs = $input.all();
base.refazer = $('Um por item').all().map((r, k) => ({ ...r.json, conteudo_atual: (docs[k].json || {}).content || '' }));
return [{ json: base }];
""", [1540, 0]))
    N.append(code("Responder", "return [{ json: $input.first().json }];", [1760, 100]))
    ligar(wf, "Pedido", "Config", "Ler planilha", "Separar", "Tem refazer?")
    wf["connections"]["Tem refazer?"] = {"main": [[{"node": "Um por item", "type": "main", "index": 0}],
                                                  [{"node": "Responder", "type": "main", "index": 0}]]}
    ligar(wf, "Um por item", "Ler roteiro atual", "Juntar", "Responder")
    return wf


def wf_receber():
    wf = novo_wf("Canal Terror · 2 · Receber roteiros")
    N = wf["nodes"]
    N.append(webhook("Roteiros chegaram", "roteiros"))
    N.append(code("Config", CONFIG_JS, [220, 100]))
    N.append(code("Separar roteiros", """
const cfg = $('Config').first().json;
const b = $('Roteiros chegaram').first().json.body || {};
const data = b.data_post || cfg.data_post;
const nomes = { avulso: 'Avulso', parte1: 'História · Parte 1', parte2: 'História · Parte 2' };
return (b.roteiros || []).map(x => ({ json: { ...x, data_post: data,
  nome_doc: `${data} · ${x.numero} · ${nomes[x.tipo] || x.tipo} · ${x.titulo}` } }));
""", [440, 100]))
    N.append(docs_criar("Criar doc", "={{ $json.nome_doc }}", [660, 100]))
    N.append(docs_escrever("Escrever roteiro", "={{ $('Separar roteiros').item.json.conteudo }}", [880, 100]))
    N.append(code("Linhas da planilha", """
const docs = $('Criar doc').all();
return $('Separar roteiros').all().map((r, k) => {
  const id = docs[k].json.id;
  return { json: { data_post: r.json.data_post, numero: r.json.numero, tipo: r.json.tipo, titulo: r.json.titulo,
    resumo: r.json.resumo, doc_id: id, doc_url: `https://docs.google.com/document/d/${id}/edit`,
    status: r.json.status || 'pendente', feedback: '', versao: 1, atualizado_em: new Date().toISOString() } };
});
""", [1100, 100]))
    N.append(sheets_append("Registrar na planilha", [1320, 100]))
    N.append(code("Mensagem", """
const cfg = $('Config').first().json;
const linhas = $('Linhas da planilha').all().map(i => i.json);
const rot = { avulso: '🎯 Avulso', parte1: '📖 História · Parte 1', parte2: '📖 História · Parte 2' };
const d = String(linhas[0] ? linhas[0].data_post : cfg.data_post).split('-').reverse().join('/');
let t = `🎬 *Roteiros de ${d}*\\n\\n`;
for (const l of linhas) t += `*${l.numero}. ${rot[l.tipo] || l.tipo}* — ${l.titulo}\\n${l.resumo}\\n${l.doc_url}\\n\\n`;
t += 'Responda:\\n• *aprovo 1 2 3* (ou *aprovo tudo*)\\n• *refaz 2: o que mudar*';
return [{ json: { texto: t, numero: cfg.whatsapp_numero, instancia: cfg.whatsapp_instancia,
  docs: linhas.map(l => ({ numero: l.numero, titulo: l.titulo, doc_url: l.doc_url })) } }];
""", [1540, 100]))
    N.append(tem_whatsapp("WhatsApp configurado?", [1760, 100]))
    N.append(whatsapp("Avisar no WhatsApp", [1980, 0]))
    N.append(code("Resposta", "return [{ json: { ok: true, docs: $('Mensagem').first().json.docs } }];", [2200, 100]))
    ligar(wf, "Roteiros chegaram", "Config", "Separar roteiros", "Criar doc", "Escrever roteiro", "Linhas da planilha",
          "Registrar na planilha", "Mensagem", "WhatsApp configurado?")
    wf["connections"]["WhatsApp configurado?"] = {"main": [[{"node": "Avisar no WhatsApp", "type": "main", "index": 0}],
                                                           [{"node": "Resposta", "type": "main", "index": 0}]]}
    ligar(wf, "Avisar no WhatsApp", "Resposta")
    return wf


def wf_revisao():
    wf = novo_wf("Canal Terror · 3 · Receber revisão")
    N = wf["nodes"]
    N.append(webhook("Revisão chegou", "revisao"))
    N.append(code("Config", CONFIG_JS, [220, 100]))
    N.append(code("Preparar", """
const b = $('Revisão chegou').first().json.body || {};
const versao = Number(b.versao_anterior || 1) + 1;
return [{ json: { ...b, versao, nome_doc: `${b.data_post} · ${b.numero} · v${versao} · ${b.titulo}` } }];
""", [440, 100]))
    N.append(docs_criar("Criar nova versão", "={{ $json.nome_doc }}", [660, 100]))
    N.append(docs_escrever("Escrever nova versão", "={{ $('Preparar').item.json.conteudo }}", [880, 100]))
    N.append(code("Atualizar linha", """
const p = $('Preparar').first().json;
const id = $('Criar nova versão').first().json.id;
return [{ json: { row_number: p.row_number, titulo: p.titulo, resumo: p.resumo, doc_id: id,
  doc_url: `https://docs.google.com/document/d/${id}/edit`, status: 'pendente', versao: p.versao,
  atualizado_em: new Date().toISOString() } }];
""", [1100, 100]))
    N.append(sheets_update("Salvar na planilha", [1320, 100]))
    N.append(code("Mensagem", """
const cfg = $('Config').first().json;
const p = $('Preparar').first().json;
const l = $('Atualizar linha').first().json;
const t = `✏️ *Nova versão do ${p.numero}* (v${l.versao}) — ${l.titulo}\\n${l.resumo}\\n${l.doc_url}\\n\\n` +
  `Responda *aprovo ${p.numero}* ou *refaz ${p.numero}: ...*`;
return [{ json: { texto: t, numero: cfg.whatsapp_numero, instancia: cfg.whatsapp_instancia, doc_url: l.doc_url } }];
""", [1540, 100]))
    N.append(tem_whatsapp("WhatsApp configurado?", [1760, 100]))
    N.append(whatsapp("Avisar no WhatsApp", [1980, 0]))
    N.append(code("Resposta", "return [{ json: { ok: true, doc_url: $('Mensagem').first().json.doc_url } }];", [2200, 100]))
    ligar(wf, "Revisão chegou", "Config", "Preparar", "Criar nova versão", "Escrever nova versão", "Atualizar linha",
          "Salvar na planilha", "Mensagem", "WhatsApp configurado?")
    wf["connections"]["WhatsApp configurado?"] = {"main": [[{"node": "Avisar no WhatsApp", "type": "main", "index": 0}],
                                                           [{"node": "Resposta", "type": "main", "index": 0}]]}
    ligar(wf, "Avisar no WhatsApp", "Resposta")
    return wf


def wf_aprovacao():
    wf = novo_wf("Canal Terror · 4 · Aprovação WhatsApp")
    N = wf["nodes"]
    N.append(webhook("Mensagem recebida", "whatsapp", resposta="onReceived"))
    N.append(code("Config", CONFIG_JS, [220, 100]))
    N.append(code("Entender comando", """
const cfg = $('Config').first().json;
const b = $('Mensagem recebida').first().json.body || {};
const d = b.data || {};
const key = d.key || {};
const msg = d.message || {};
const texto = (msg.conversation || (msg.extendedTextMessage || {}).text || b.texto || '').trim();
// só mensagens novas da conversa do dono (a instância é o próprio número dele: conversa "Você")
if (b.event && !/messages[._]upsert/i.test(b.event)) return [];
const de = String(key.remoteJid || b.numero || '').replace(/\\D/g, '');
const dono = cfg.whatsapp_numero.replace(/\\D/g, '');
if (!dono || !de || de.slice(-8) !== dono.slice(-8)) return [];
let m;
if ((m = texto.match(/^aprov\\w*\\s*(.*)$/i))) {
  const resto = m[1].toLowerCase();
  const numeros = /tud|todos/.test(resto) || !resto ? [1, 2, 3] : (resto.match(/\\d/g) || []).map(Number);
  return [{ json: { acao: 'aprovar', numeros, feedback: '' } }];
}
if ((m = texto.match(/^refa\\w*\\s*(\\d)\\s*[:\\-–]?\\s*([\\s\\S]*)$/i))) {
  return [{ json: { acao: 'refazer', numeros: [Number(m[1])], feedback: m[2].trim() } }];
}
return [];
""", [440, 100]))
    N.append(sheets_read("Ler planilha", [660, 100]))
    N.append(code("Atualizar status", f"""
const cmd = $('Entender comando').first().json;
const linhas = $input.all().map(i => i.json).filter(r => {TIPOS_VALIDOS}.includes(r.tipo) && r.data_post);
const ultimaData = linhas.map(r => String(r.data_post)).sort().pop();
const alvo = linhas.filter(r => String(r.data_post) === ultimaData && cmd.numeros.includes(Number(r.numero)));
return alvo.map(r => ({{ json: {{ row_number: r.row_number,
  status: cmd.acao === 'aprovar' ? 'aprovado' : 'refazer',
  feedback: cmd.acao === 'refazer' ? cmd.feedback : (r.feedback || ''),
  atualizado_em: new Date().toISOString(), _titulo: r.titulo, _numero: r.numero, _doc_id: r.doc_id, _data: r.data_post, _tipo: r.tipo }} }}));
""", [880, 100]))
    N.append(code("Só colunas", """
return $input.all().map(i => { const { _titulo, _numero, _doc_id, _data, _tipo, ...resto } = i.json; return { json: resto }; });
""", [1100, 100]))
    N.append(sheets_update("Salvar na planilha", [1320, 100]))
    N.append(code("Resposta", """
const cfg = $('Config').first().json;
const cmd = $('Entender comando').first().json;
const itens = $('Atualizar status').all().map(i => i.json);
let t;
if (!itens.length) t = '⚠️ Não achei esse roteiro na planilha.';
else if (cmd.acao === 'aprovar') t = '✅ Aprovado' + (itens.length > 1 ? 's' : '') + ':\\n' + itens.map(r => `${r._numero}. ${r._titulo}`).join('\\n');
else t = `📝 Anotado! Vou reescrever o ${itens[0]._numero} (${itens[0]._titulo}) na próxima rodada e te mando a nova versão aqui.`;
return [{ json: { texto: t, numero: cfg.whatsapp_numero, instancia: cfg.whatsapp_instancia } }];
""", [1540, 100], executeOnce=True))
    N.append(whatsapp("Responder", [1760, 100]))
    N.append(code("Pedidos de voz", """
if ($('Entender comando').first().json.acao !== 'aprovar') return [];
return $('Atualizar status').all().map(i => ({ json: { row_number: i.json.row_number, data_post: i.json._data,
  numero: i.json._numero, tipo: i.json._tipo, titulo: i.json._titulo, doc_id: i.json._doc_id } }));
""", [1980, 100]))
    N.append(node("Disparar vozes", "n8n-nodes-base.executeWorkflow", 1.2, {
        "source": "database",
        "workflowId": {"__rl": True, "value": CFG.get("id_workflow_vozes", ""), "mode": "id"},
        "mode": "each",
        "options": {"waitForSubWorkflow": True}}, [2200, 100], onError="continueRegularOutput"))
    ligar(wf, "Mensagem recebida", "Config", "Entender comando", "Ler planilha", "Atualizar status", "Só colunas",
          "Salvar na planilha", "Resposta", "Responder", "Pedidos de voz", "Disparar vozes")
    return wf


def wf_upload():
    wf = novo_wf("Canal Terror · 5 · Iniciar upload de vídeo")
    N = wf["nodes"]
    N.append(webhook("Pedido de upload", "upload"))
    N.append(code("Preparar", f"""
const b = $('Pedido de upload').first().json.body || {{}};
if (!b.nome || !b.tamanho) throw new Error('envie nome e tamanho');
return [{{ json: {{ nome: String(b.nome), tamanho: String(b.tamanho), mime: b.mime || 'video/mp4',
  pasta: b.pasta || {js(IDS.get('pasta_videos_id', ''))} }} }}];
""", [220, 100]))
    N.append(node("Abrir upload no Drive", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST",
        "url": "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true",
        "authentication": "predefinedCredentialType",
        "nodeCredentialType": "googleDriveOAuth2Api",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "X-Upload-Content-Type", "value": "={{ $json.mime }}"},
            {"name": "X-Upload-Content-Length", "value": "={{ $json.tamanho }}"}]},
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ name: $json.nome, parents: [$json.pasta] }) }}",
        "options": {"response": {"response": {"fullResponse": True}}},
    }, [440, 100], {"googleDriveOAuth2Api": CRED["googleDriveOAuth2Api"]}))
    N.append(code("Responder", """
const h = $input.first().json.headers || {};
return [{ json: { upload_url: h.location || h.Location || '' } }];
""", [660, 100]))
    ligar(wf, "Pedido de upload", "Preparar", "Abrir upload no Drive", "Responder")
    return wf


EXTENSO_JS = r"""
const U = 'zero um dois três quatro cinco seis sete oito nove dez onze doze treze catorze quinze dezesseis dezessete dezoito dezenove'.split(' ');
const D = '_ _ vinte trinta quarenta cinquenta sessenta setenta oitenta noventa'.split(' ');
const C = '_ cento duzentos trezentos quatrocentos quinhentos seiscentos setecentos oitocentos novecentos'.split(' ');
function ext(n) {
  if (n < 20) return U[n];
  if (n < 100) return D[Math.floor(n / 10)] + (n % 10 ? ' e ' + U[n % 10] : '');
  if (n === 100) return 'cem';
  if (n < 1000) return C[Math.floor(n / 100)] + (n % 100 ? ' e ' + ext(n % 100) : '');
  if (n < 1000000) { const m = Math.floor(n / 1000), r = n % 1000;
    return (m === 1 ? 'mil' : ext(m) + ' mil') + (r ? (r < 100 || r % 100 === 0 ? ' e ' : ' ') + ext(r) : ''); }
  return String(n);
}
function hora(n) { return ext(n).replace(/\bum$/, 'uma').replace(/\bdois$/, 'duas'); }
function falar(t) {
  return t.replace(/(\d{1,2})h(\d{2})/g, (_, h, m) => hora(+h) + ' e ' + ext(+m))
          .replace(/(\d{1,2})\s?h\b/g, (_, h) => hora(+h) + (+h === 1 ? ' hora' : ' horas'))
          .replace(/(\d+)\s?%/g, (_, n) => ext(+n) + ' por cento')
          .replace(/\d+/g, n => ext(+n))
          .replace(/\[pausa\]/gi, '<break time="1.0s" />');
}
"""


def wf_vozes():
    wf = novo_wf("Canal Terror · 6 · Vozes ElevenLabs")
    N = wf["nodes"]
    N.append(webhook("Roteiro aprovado", "vozes", resposta="onReceived"))
    N.append(node("Chamado pela aprovação", "n8n-nodes-base.executeWorkflowTrigger", 1.1,
                  {"inputSource": "passthrough"}, [0, 300]))
    N.append(code("Entrada", "const j = $input.first().json; return [{ json: { body: j.body || j } }];", [110, 100]))
    N.append(code("Config", CONFIG_JS, [220, 100]))
    N.append(node("Criar pasta do roteiro", "n8n-nodes-base.googleDrive", 3, {
        "resource": "folder",
        "name": "={{ [$('Entrada').first().json.body.data_post, $('Entrada').first().json.body.numero, $('Entrada').first().json.body.titulo].join(' · ') }}",
        "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
        "folderId": {"__rl": True, "value": IDS.get("pasta_audios_id", ""), "mode": "id"},
        "options": {}}, [440, 100], {"googleDriveOAuth2Api": CRED["googleDriveOAuth2Api"]}))
    N.append(node("Ler roteiro", "n8n-nodes-base.googleDocs", 2, {
        "operation": "get", "documentURL": "={{ $('Entrada').first().json.body.doc_id }}", "simple": True},
        [660, 100], {"googleDocsOAuth2Api": CRED["googleDocsOAuth2Api"]}))
    N.append(code("Separar falas", EXTENSO_JS + f"""
const texto = $input.first().json.content || '';
const falas = [...texto.matchAll(/Narra[cç][aã]o:\\s*["“]([\\s\\S]*?)["”]\\s*(?:\\n|$)/g)].map(m => m[1].trim());
if (!falas.length) throw new Error('Não encontrei linhas "Narração:" no roteiro');
const limpo = t => t.replace(/\\[pausa\\]/gi, '').trim();
return falas.map((f, k) => {{
  const body = {{ text: falar(f), model_id: {js(VOZ['model_id'])}, voice_settings: {js(VOZ['voice_settings'])} }};
  if (k > 0) body.previous_text = limpo(falas[k - 1]);
  if (k < falas.length - 1) body.next_text = limpo(falas[k + 1]);
  const simples = falar(f).replace(/<break[^>]*>/g, '...');
  return {{ json: {{ nome: 'cena' + String(k + 1).padStart(2, '0') + '.mp3', body, caracteres: body.text.length, texto_simples: simples }} }};
}});
""", [880, 100]))
    p = {
        "method": "POST",
        "url": f"https://api.elevenlabs.io/v1/text-to-speech/{VOZ['voice_id']}?output_format=mp3_44100_128",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify($json.body) }}",
        "options": {"response": {"response": {"responseFormat": "file"}},
                    "batching": {"batch": {"batchSize": 1, "batchInterval": 2500}}, "timeout": 120000},
    }
    N.append(node("Gerar voz", "n8n-nodes-base.httpRequest", 4.2, p, [1100, 100],
                  {"httpHeaderAuth": ELEVEN} if ELEVEN else None, onError="continueErrorOutput",
                  retryOnFail=True, maxTries=3, waitBetweenTries=5000))
    # reserva: se o ElevenLabs falhar (ex.: créditos acabaram), gera a mesma fala na OpenAI
    instr = ("Narre em português do Brasil, com sotaque brasileiro natural (não português de Portugal). "
             "Voz de homem jovem, tom de história de terror contada para um amigo: baixa, calma, "
             "com tensão crescente e pausas curtas antes das frases de impacto.")
    N.append(node("Voz reserva (OpenAI)", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": "https://api.openai.com/v1/audio/speech",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ model: 'gpt-4o-mini-tts', voice: " + js(CFG.get('voz_reserva_openai', 'onyx')) +
                    ", response_format: 'mp3', instructions: " + js(instr) + ", input: $('Separar falas').item.json.texto_simples }) }}",
        "options": {"response": {"response": {"responseFormat": "file"}}, "timeout": 120000},
    }, [1100, 300], {"openAiApi": CRED["openAiApi"]}))
    N.append(node("Salvar no Drive", "n8n-nodes-base.googleDrive", 3, {
        "name": "={{ $('Separar falas').item.json.nome }}",
        "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
        "folderId": {"__rl": True, "value": "={{ $('Criar pasta do roteiro').first().json.id }}", "mode": "id"},
        "options": {}}, [1320, 100], {"googleDriveOAuth2Api": CRED["googleDriveOAuth2Api"]}))
    N.append(code("Marcar voz pronta", """
const b = $('Entrada').first().json.body;
return [{ json: { row_number: b.row_number, status: 'voz pronta', atualizado_em: new Date().toISOString() } }];
""", [1540, 100], executeOnce=True))
    N.append(sheets_update("Salvar status", [1760, 100]))
    N.append(code("Mensagem", """
const cfg = $('Config').first().json;
const b = $('Entrada').first().json.body;
const pasta = $('Criar pasta do roteiro').first().json.id;
const n = $('Separar falas').all().length;
const chars = $('Separar falas').all().reduce((s, i) => s + i.json.caracteres, 0);
let reserva = 0; try { reserva = $('Voz reserva (OpenAI)').isExecuted ? $('Voz reserva (OpenAI)').all().length || 1 : 0; } catch (e) {}
const t = `🎙️ *Vozes prontas do ${b.numero}* — ${b.titulo}\\n${n} áudios (${chars} caracteres)` +
  (reserva ? `\\n⚠️ Parte dos áudios saiu com a voz reserva da OpenAI (o ElevenLabs falhou): confira os créditos do ElevenLabs.` : '') +
  `\\nhttps://drive.google.com/drive/folders/${pasta}\\n\\n` +
  'Agora é só gerar as imagens da lista do roteiro e me mandar pra montar o vídeo 🎬';
return [{ json: { texto: t, numero: cfg.whatsapp_numero, instancia: cfg.whatsapp_instancia } }];
""", [1980, 100], executeOnce=True))
    N.append(whatsapp("Avisar no WhatsApp", [2200, 100]))
    ligar(wf, "Roteiro aprovado", "Entrada")
    ligar(wf, "Chamado pela aprovação", "Entrada")
    ligar(wf, "Entrada", "Config", "Criar pasta do roteiro", "Ler roteiro", "Separar falas", "Gerar voz")
    wf["connections"]["Gerar voz"] = {"main": [[{"node": "Salvar no Drive", "type": "main", "index": 0}],
                                               [{"node": "Voz reserva (OpenAI)", "type": "main", "index": 0}]]}
    ligar(wf, "Voz reserva (OpenAI)", "Salvar no Drive")
    ligar(wf, "Salvar no Drive", "Marcar voz pronta", "Salvar status", "Mensagem", "Avisar no WhatsApp")
    return wf


SUFIXO_IMG = ("flat 2D vector background, simple geometric shapes, thick clean outlines, dark muted colors, "
              "soft dark vignette, minimalist web-animation style, no characters, empty scene, no text, vertical 9:16")


def wf_imagens():
    wf = novo_wf("Canal Terror · 7 · Imagens toda noite")
    N = wf["nodes"]
    N.append(node("Toda noite 22h", "n8n-nodes-base.scheduleTrigger", 1.2,
                  {"rule": {"interval": [{"field": "cronExpression", "expression": "0 22 * * *"}]}}, [0, 0]))
    N.append(webhook("Gerar agora (teste)", "imagens", resposta="onReceived", pos=(0, 200)))
    N.append(code("Config", CONFIG_JS, [220, 100]))
    N.append(sheets_read("Ler planilha", [440, 100]))
    N.append(code("Roteiros sem imagem", f"""
return $input.all().map(i => i.json)
  .filter(r => {TIPOS_VALIDOS}.includes(r.tipo) && ['aprovado', 'voz pronta'].includes(String(r.status)))
  .map(r => ({{ json: {{ row_number: r.row_number, data_post: r.data_post, numero: r.numero, tipo: r.tipo,
                        titulo: r.titulo, doc_id: r.doc_id, status: r.status }} }}));
""", [660, 100]))
    N.append(node("Um roteiro por vez", "n8n-nodes-base.splitInBatches", 3, {"batchSize": 1, "options": {}}, [880, 100]))
    N.append(node("Criar pasta", "n8n-nodes-base.googleDrive", 3, {
        "resource": "folder",
        "name": "={{ [$json.data_post, $json.numero, $json.titulo].join(' · ') }}",
        "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
        "folderId": {"__rl": True, "value": IDS.get("pasta_imagens_id", ""), "mode": "id"},
        "options": {}}, [1100, 200], {"googleDriveOAuth2Api": CRED["googleDriveOAuth2Api"]}))
    N.append(node("Ler roteiro", "n8n-nodes-base.googleDocs", 2, {
        "operation": "get", "documentURL": "={{ $('Um roteiro por vez').item.json.doc_id }}", "simple": True},
        [1320, 200], {"googleDocsOAuth2Api": CRED["googleDocsOAuth2Api"]}))
    N.append(code("Separar prompts", f"""
const texto = $input.first().json.content || '';
const ini = texto.search(/IMAGENS NOVAS PARA GERAR/i);
const fim = texto.search(/\\nPOSTAGEM/i);
const bloco = ini >= 0 ? texto.slice(ini, fim > ini ? fim : undefined) : '';
const out = [];
for (const linha of bloco.split('\\n')) {{
  const m = linha.match(/^\\s*[-•*]\\s*([^:`]+?)\\s*:\\s*`?([^`]+)`?/);
  if (!m) continue;
  const nome = m[1].trim().toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').replace(/[^a-z0-9_]+/g, '_').replace(/^_|_$/g, '');
  let p = m[2].replace(/\\+\\s*sufixo.*/i, '').trim().replace(/[,.]$/, '');
  if (!nome || !p) continue;
  out.push({{ json: {{ nome, prompt: p + ', ' + {js(SUFIXO_IMG)} }} }});
}}
return out;
""", [1540, 200]))
    N.append(node("Gerar imagem", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": "https://api.openai.com/v1/images/generations",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ model: " + js(CFG.get('modelo_imagem', 'gpt-image-2')) +
                    ", prompt: $json.prompt, size: '1024x1536', quality: " + js(CFG.get('qualidade_imagem', 'medium')) + ", n: 1 }) }}",
        "options": {"timeout": 300000, "batching": {"batch": {"batchSize": 1, "batchInterval": 1000}}},
    }, [1760, 200], {"openAiApi": CRED["openAiApi"]}, onError="continueRegularOutput"))
    N.append(code("Virar arquivo", """
const pedidos = $('Separar prompts').all();
const out = [];
for (const [k, it] of $input.all().entries()) {
  const b64 = it.json.data && it.json.data[0] && it.json.data[0].b64_json;
  const nome = pedidos[k].json.nome;
  if (!b64) { out.push({ json: { nome, erro: true } }); continue; }
  const bin = await this.helpers.prepareBinaryData(Buffer.from(b64, 'base64'), nome + '.png', 'image/png');
  out.push({ json: { nome, erro: false }, binary: { data: bin } });
}
return out.filter(o => !o.json.erro).length ? out.filter(o => !o.json.erro) : [{ json: { nada: true } }];
""", [1980, 200]))
    N.append(node("Salvar imagem", "n8n-nodes-base.googleDrive", 3, {
        "name": "={{ $json.nome }}.png",
        "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
        "folderId": {"__rl": True, "value": "={{ $('Criar pasta').first().json.id }}", "mode": "id"},
        "options": {}}, [2200, 200], {"googleDriveOAuth2Api": CRED["googleDriveOAuth2Api"]}, onError="continueRegularOutput"))
    N.append(code("Resumo do roteiro", """
const r = $('Um roteiro por vez').first().json;
const pedidos = $('Separar prompts').all().length;
const ok = $('Virar arquivo').all().filter(i => i.binary).length;
return [{ json: { row_number: r.row_number, status: ok ? 'imagens prontas' : r.status, atualizado_em: new Date().toISOString(),
  _linha: `• *${r.numero}. ${r.titulo}* — ${ok}/${pedidos} imagens\\nhttps://drive.google.com/drive/folders/${$('Criar pasta').first().json.id}` } }];
""", [2420, 200], executeOnce=True))
    N.append(code("Só colunas", "const { _linha, ...resto } = $input.first().json; return [{ json: resto }];", [2640, 200]))
    N.append(sheets_update("Salvar status", [2860, 200]))
    N.append(code("Mensagem final", """
const cfg = $('Config').first().json;
let linhas = [];
try { linhas = $('Resumo do roteiro').all().map(i => i.json._linha); } catch (e) {}
if (!linhas.length) return [];
const t = '🎨 *Imagens da noite prontas*\\n\\n' + linhas.join('\\n\\n') + '\\n\\nAs poses do Lucas eu reaproveito. Quando quiser, me chama pra montar os vídeos 🎬';
return [{ json: { texto: t, numero: cfg.whatsapp_numero, instancia: cfg.whatsapp_instancia } }];
""", [1100, 0]))
    N.append(whatsapp("Avisar no WhatsApp", [1320, 0]))
    ligar(wf, "Toda noite 22h", "Config")
    ligar(wf, "Gerar agora (teste)", "Config")
    ligar(wf, "Config", "Ler planilha", "Roteiros sem imagem", "Um roteiro por vez")
    wf["connections"]["Um roteiro por vez"] = {"main": [[{"node": "Mensagem final", "type": "main", "index": 0}],
                                                        [{"node": "Criar pasta", "type": "main", "index": 0}]]}
    ligar(wf, "Criar pasta", "Ler roteiro", "Separar prompts", "Gerar imagem", "Virar arquivo", "Salvar imagem",
          "Resumo do roteiro", "Só colunas", "Salvar status", "Um roteiro por vez")
    ligar(wf, "Mensagem final", "Avisar no WhatsApp")
    return wf


def wf_drive():
    """Lista uma pasta do Drive (?pasta=ID) ou baixa um arquivo (?id=ID). Usado pelo gerador de vídeos."""
    wf = novo_wf("Canal Terror · 8 · Drive (listar e baixar)")
    N = wf["nodes"]
    N.append(webhook("Pedido", "drive", metodo="GET", resposta="responseNode"))
    N.append(node("Listar ou baixar?", "n8n-nodes-base.if", 2, {
        "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                       "conditions": [{"id": "p", "leftValue": "={{ $json.query.pasta }}", "rightValue": "",
                                       "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}}],
                       "combinator": "and"}, "options": {}}, [220, 100]))
    N.append(node("Listar pasta", "n8n-nodes-base.googleDrive", 3, {
        "resource": "fileFolder", "returnAll": True,
        "filter": {"folderId": {"__rl": True, "value": "={{ $json.query.pasta }}", "mode": "id"}},
        "options": {"fields": ["id", "name", "mimeType", "size"]}},
        [440, 0], {"googleDriveOAuth2Api": CRED["googleDriveOAuth2Api"]}, alwaysOutputData=True))
    N.append(code("Juntar lista", "return [{ json: { arquivos: $input.all().map(i => i.json).filter(f => f.id) } }];", [660, 0]))
    N.append(node("Responder lista", "n8n-nodes-base.respondToWebhook", 1.1, {"respondWith": "json",
              "responseBody": "={{ JSON.stringify($json) }}", "options": {}}, [880, 0]))
    N.append(node("Baixar arquivo", "n8n-nodes-base.googleDrive", 3, {
        "operation": "download", "fileId": {"__rl": True, "value": "={{ $json.query.id }}", "mode": "id"}, "options": {}},
        [440, 200], {"googleDriveOAuth2Api": CRED["googleDriveOAuth2Api"]}))
    N.append(node("Responder arquivo", "n8n-nodes-base.respondToWebhook", 1.1, {"respondWith": "binary", "options": {}},
                  [660, 200]))
    ligar(wf, "Pedido", "Listar ou baixar?")
    wf["connections"]["Listar ou baixar?"] = {"main": [[{"node": "Listar pasta", "type": "main", "index": 0}],
                                                       [{"node": "Baixar arquivo", "type": "main", "index": 0}]]}
    ligar(wf, "Listar pasta", "Juntar lista", "Responder lista")
    ligar(wf, "Baixar arquivo", "Responder arquivo")
    return wf


# --------------------------------------------------------------------------- #
def api(metodo, caminho, corpo=None):
    cmd = ["curl", "-sS", "--max-time", "60", "-X", metodo, f"{N8N}/api/v1{caminho}", "-H", "Content-Type: application/json"]
    if corpo is not None:
        cmd += ["-d", json.dumps(corpo, ensure_ascii=False)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return json.loads(out) if out.strip().startswith(("{", "[")) else {"raw": out}


def publicar(wf, ativar):
    existentes = api("GET", "/workflows?limit=250").get("data", [])
    atual = next((w for w in existentes if w["name"] == wf["name"]), None)
    if atual:
        r = api("PUT", f"/workflows/{atual['id']}", wf)
        wid = atual["id"]
        print("atualizado:", wf["name"], wid, "" if r.get("id") else r)
    else:
        r = api("POST", "/workflows", wf)
        wid = r.get("id")
        print("criado:", wf["name"], wid or r)
    if ativar and wid and "Imagens toda noite" not in wf["name"]:
        a = api("POST", f"/workflows/{wid}/activate")
        print("   ativo:", a.get("active", a))
    return wid


if __name__ == "__main__":
    wfs = [wf_contexto(), wf_receber(), wf_revisao(), wf_aprovacao(), wf_upload(), wf_vozes(), wf_imagens(), wf_drive()]
    for wf in wfs:
        nome = wf["name"].split("·")[-1].strip().lower().replace(" ", "_")
        (AQUI / f"wf_{nome}.json").write_text(json.dumps(wf, ensure_ascii=False, indent=1), encoding="utf-8")
    if "--so-json" not in sys.argv:
        # apaga os workflows da versão anterior (que chamavam a API do Claude direto)
        antigos = {"Canal Terror · 1 · Roteiros diários", "Canal Terror · 2 · Aprovação WhatsApp"}
        for w in api("GET", "/workflows?limit=250").get("data", []):
            if w["name"] in antigos:
                api("DELETE", f"/workflows/{w['id']}")
                print("removido (versão antiga):", w["name"])
        ids = {wf["name"]: publicar(wf, "--ativar" in sys.argv) for wf in wfs}
        ids["webhooks"] = {k: f"{N8N}/webhook/canal-terror-{k}-{SUF}" for k in ("contexto", "roteiros", "revisao", "whatsapp", "upload", "vozes", "imagens", "drive")}
        (AQUI / "workflows_publicados.json").write_text(json.dumps(ids, ensure_ascii=False, indent=1), encoding="utf-8")
