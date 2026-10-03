#!/usr/bin/env python3
"""Envia itens da fila do estúdio para a fila do webapp — o estúdio é o motor,
o webapp aprova, agenda e publica.

Uso:
    python enviar_webapp.py enviar clientes/<h>/fila/<item> [<item> ...]
    python enviar_webapp.py enviar --cliente <handle> --todos     # tudo que ainda não foi enviado
    python enviar_webapp.py status [--cliente <handle>]           # situação de cada item no webapp

O que vai:
    - item em rascunho ou aguardando aprovação → chega no webapp aguardando aprovação;
      a equipe aprova lá, vendo a prévia.
    - item aprovado no estúdio → leva a aprovação junto (nome, data e impressão
      digital). Antes de enviar, este script recalcula a impressão e recusa se algo
      mudou; o webapp baixa a mídia, recalcula de novo e só aceita se bater.
    - post com avatar digital não vai: a verificação de consentimento é do estúdio,
      e ele continua publicando pelo `publicar.py`.

Depois de enviado, o item fica marcado no post.json (campo `webapp`) e o
`publicar.py` passa a recusá-lo — quem publica é o webapp, nunca os dois.

Configuração (.env na raiz ou ambiente):
    ESTUDIO_WEBAPP_URL   padrão https://redes-sociais-webapp.vercel.app
    ESTUDIO_API_CHAVE    a mesma ESTUDIO_API_CHAVE definida na Vercel
A mídia sobe direto para o Vercel Blob por `webapp/scripts/subir-midias.mjs`
(Node 18+, `cd webapp && npm install` uma vez).
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import fila  # noqa: E402
import publicar  # noqa: E402

SUBIR = fila.RAIZ / "webapp" / "scripts" / "subir-midias.mjs"
ENVIAVEIS = {"rascunho", "aguardando_aprovacao", "aprovado"}


def config():
    publicar.carregar_env()
    url = os.environ.get("ESTUDIO_WEBAPP_URL", "https://redes-sociais-webapp.vercel.app").rstrip("/")
    chave = os.environ.get("ESTUDIO_API_CHAVE", "")
    if len(chave) < 32:
        sys.exit("defina ESTUDIO_API_CHAVE (a mesma da Vercel, 32+ caracteres) no .env ou no ambiente")
    return url, chave


def pedir(metodo, url, chave, corpo=None):
    import requests
    r = requests.request(metodo, url, json=corpo, headers={"Authorization": f"Bearer {chave}"}, timeout=120)
    try:
        dados = r.json()
    except ValueError:
        dados = {"erro": r.text[:300]}
    return r.status_code, dados


def subir_midias(url, chave, post, item: Path):
    if not (fila.RAIZ / "webapp" / "node_modules" / "@vercel" / "blob").exists():
        sys.exit("falta instalar o webapp para subir a mídia: cd webapp && npm install")
    arquivos = [(item / m).resolve() for m in post["midias"]] + ([(item / post["capa"]).resolve()] if post.get("capa") else [])
    try:
        r = subprocess.run(["node", str(SUBIR), url, post["cliente"], item.name, *map(str, arquivos)],
                           capture_output=True, text=True, timeout=1800, cwd=fila.RAIZ / "webapp",
                           env={**os.environ, "ESTUDIO_API_CHAVE": chave, "VERCEL_BLOB_RETRIES": "3"})
    except subprocess.TimeoutExpired:
        raise RuntimeError("upload da mídia passou de 30 minutos — confira a rede até *.blob.vercel-storage.com")
    if r.returncode != 0:
        linhas = [l for l in r.stderr.splitlines() if l.startswith("erro: ")] or r.stderr.strip().splitlines()[-1:]
        raise RuntimeError(f"upload da mídia falhou: {linhas[0].removeprefix('erro: ') if linhas else 'sem detalhe'}")
    enviadas = json.loads(r.stdout)
    midias = enviadas[: len(post["midias"])]
    capa = enviadas[len(post["midias"])] if post.get("capa") else None
    return midias, capa


def enviar_item(item: Path, url, chave) -> bool:
    post = fila.ler(item)
    nome = item.name
    if post.get("webapp"):
        print(f"· {nome}: já enviado ao webapp ({post['webapp']['id']})")
        return True
    if post["status"] not in ENVIAVEIS:
        print(f"· {nome}: status '{post['status']}' — não se envia")
        return True
    if post.get("avatares"):
        print(f"✗ {nome}: post com avatar digital é publicado pelo estúdio (consentimento), não pelo webapp")
        return False
    aprovacao = None
    if post["status"] == "aprovado":
        if not post.get("aprovacao") or fila.impressao(item, post) != post["aprovacao"]["impressao"]:
            print(f"✗ {nome}: mídia, legenda ou horário mudaram depois da aprovação — precisa de nova aprovação")
            return False
        a = post["aprovacao"]
        aprovacao = {"por": a["por"], "em": a["em"], "impressao": a["impressao"], "mensagem": a.get("mensagem")}

    try:
        midias, capa = subir_midias(url, chave, post, item)
    except RuntimeError as e:
        print(f"✗ {nome}: {e}")
        return False
    corpo = {
        "nome": nome, "cliente": post["cliente"], "tipo": post["tipo"], "legenda": post["legenda"],
        "agendado_para": post["agendado_para"], "thumb_offset_ms": post.get("thumb_offset_ms"),
        "avatares": post.get("avatares") or [], "midias": midias, "capa": capa, "aprovacao": aprovacao,
    }
    codigo, dados = pedir("POST", f"{url}/api/estudio/itens", chave, corpo)
    if codigo not in (200, 201):
        detalhes = "; ".join(dados.get("detalhes", []))
        print(f"✗ {nome}: webapp recusou ({codigo}): {dados.get('erro')}{' — ' + detalhes if detalhes else ''}")
        return False

    quando = fila.agora().isoformat(timespec="seconds")
    post["webapp"] = {"id": dados["id"], "enviado_em": quando, "url": f"{url}/fila/{dados['id']}"}
    post["historico"].append({"em": quando, "evento": f"enviado ao webapp ({dados['status']})"})
    fila.gravar(item, post)
    print(f"✓ {nome}: no webapp como '{dados['status']}' · {post['webapp']['url']}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enviar")
    e.add_argument("itens", nargs="*")
    e.add_argument("--cliente")
    e.add_argument("--todos", action="store_true")
    s = sub.add_parser("status")
    s.add_argument("--cliente")
    a = ap.parse_args()
    url, chave = config()

    if a.cmd == "status":
        codigo, dados = pedir("GET", f"{url}/api/estudio/itens" + (f"?cliente={a.cliente}" if a.cliente else ""), chave)
        if codigo != 200:
            sys.exit(f"webapp respondeu {codigo}: {dados.get('erro')}")
        for i in dados:
            extra = i.get("permalink") or i.get("erro") or i.get("rejeicao") or ""
            print(f"{i['status']:<22} {i['tipo']:<9} {i['agendado_para'] or '-':<26} {i['id']}  {extra}")
        return

    if a.todos:
        if not a.cliente:
            sys.exit("--todos precisa de --cliente")
        itens = sorted(p.parent for p in (fila.RAIZ / "clientes" / a.cliente / "fila").glob("*/post.json"))
    else:
        itens = [Path(i) for i in a.itens]
    if not itens:
        sys.exit("nenhum item — passe os caminhos ou --cliente <handle> --todos")
    ok = True
    for item in itens:
        ok &= enviar_item(item, url, chave)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
