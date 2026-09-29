#!/usr/bin/env python3
"""Publica no Instagram pela Graph API os itens APROVADOS da fila.

Uso:
    python publicar.py item clientes/<h>/fila/<item>            # respeita o agendamento
    python publicar.py item clientes/<h>/fila/<item> --agora    # ignora o horário (item ainda precisa estar aprovado)
    python publicar.py vencidos [--cliente <h>]                 # tudo aprovado cujo horário já passou (rotina agendada)
    python publicar.py metricas clientes/<h>/fila/<item>        # insights de um item publicado
    python publicar.py conta --cliente <h>                      # confere token, conta e cota de publicação
    Qualquer comando aceita --simular: mostra o que faria, sem chamar a API nem subir mídia.

Credenciais (em .env na raiz ou no ambiente — nunca no repositório):
    IG_<HANDLE>_USER_ID     id da conta profissional do Instagram
    IG_<HANDLE>_TOKEN       token de acesso de longa duração
    IG_GRAPH_HOST           graph.facebook.com (login do Facebook, padrão) ou graph.instagram.com
    IG_GRAPH_VERSION        ex. v23.0
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_BUCKET   hospedagem temporária da mídia
<HANDLE> é o @ em maiúsculas com tudo que não é letra/número trocado por _.

Travas:
    - só publica item com status "aprovado" e impressão digital idêntica à aprovada
    - consulta a cota (content_publishing_limit) antes de publicar
    - nunca publica duas vezes: item publicado não volta para a fila
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import fila  # noqa: E402
import hospedar  # noqa: E402

VID = {".mp4", ".mov"}


def carregar_env():
    arq = fila.RAIZ / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def chave(handle):
    return re.sub(r"[^A-Z0-9]", "_", handle.upper())


class Graph:
    def __init__(self, handle, simular=False):
        self.simular = simular
        k = chave(handle)
        self.user_id = os.environ.get(f"IG_{k}_USER_ID")
        self.token = os.environ.get(f"IG_{k}_TOKEN")
        host = os.environ.get("IG_GRAPH_HOST", "graph.facebook.com")
        versao = os.environ.get("IG_GRAPH_VERSION", "v23.0")
        self.base = f"https://{host}/{versao}"
        if not simular and not (self.user_id and self.token):
            sys.exit(f"credenciais ausentes: defina IG_{k}_USER_ID e IG_{k}_TOKEN no .env "
                     "(veja references/configuracao-meta.md)")
        self.user_id = self.user_id or "<IG_USER_ID>"

    def chamar(self, metodo, caminho, **params):
        if self.simular:
            visiveis = {k: (v[:60] + "…" if isinstance(v, str) and len(v) > 60 else v) for k, v in params.items()}
            print(f"  [simulado] {metodo} {self.base}/{caminho} {visiveis}")
            return {"id": f"simulado-{caminho.split('/')[0]}-{int(time.time() * 1000) % 100000}",
                    "status_code": "FINISHED", "permalink": "https://www.instagram.com/p/SIMULADO/",
                    "quota_usage": 0, "config": {"quota_total": 100}}
        import requests
        params["access_token"] = self.token
        url = f"{self.base}/{caminho}"
        for tentativa in range(4):
            r = requests.request(metodo, url, params=params if metodo == "GET" else None,
                                 data=params if metodo == "POST" else None, timeout=60)
            if r.status_code < 500 and r.status_code != 429:
                break
            time.sleep(2 ** (tentativa + 1))
        dados = r.json() if r.headers.get("content-type", "").startswith(("application/json", "text/javascript")) else {}
        if r.status_code >= 400 or "error" in dados:
            erro = dados.get("error", {})
            raise RuntimeError(f"Graph API {r.status_code} em {caminho}: {erro.get('message', r.text[:300])} "
                               f"(code {erro.get('code')}, subcode {erro.get('error_subcode')})")
        return dados

    def cota(self):
        d = self.chamar("GET", f"{self.user_id}/content_publishing_limit", fields="quota_usage,config")
        dados = d.get("data", [d])[0]
        return dados.get("quota_usage", 0), dados.get("config", {}).get("quota_total", 100)

    def aguardar(self, container, limite_s=600):
        inicio = time.time()
        while True:
            d = self.chamar("GET", container, fields="status_code,status")
            estado = d.get("status_code")
            if estado == "FINISHED":
                return
            if estado in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"container {container} {estado}: {d.get('status')}")
            if time.time() - inicio > limite_s:
                raise RuntimeError(f"container {container} não ficou pronto em {limite_s}s (último: {estado})")
            time.sleep(5)


def criar_containers(g: Graph, post, urls, url_capa):
    tipo, legenda = post["tipo"], post["legenda"]
    ehvideo = [Path(m).suffix.lower() in VID for m in post["midias"]]
    if tipo == "feed":
        return g.chamar("POST", f"{g.user_id}/media", image_url=urls[0], caption=legenda)["id"]
    if tipo == "reel":
        p = {"media_type": "REELS", "video_url": urls[0], "caption": legenda, "share_to_feed": "true"}
        if url_capa:
            p["cover_url"] = url_capa
        elif post.get("thumb_offset_ms") is not None:
            p["thumb_offset"] = post["thumb_offset_ms"]
        c = g.chamar("POST", f"{g.user_id}/media", **p)["id"]
        g.aguardar(c)
        return c
    if tipo == "story":
        campo = "video_url" if ehvideo[0] else "image_url"
        c = g.chamar("POST", f"{g.user_id}/media", media_type="STORIES", **{campo: urls[0]})["id"]
        if ehvideo[0]:
            g.aguardar(c)
        return c
    # carrossel
    filhos = []
    for url, video in zip(urls, ehvideo):
        p = {"is_carousel_item": "true"}
        p.update({"media_type": "VIDEO", "video_url": url} if video else {"image_url": url})
        filhos.append(g.chamar("POST", f"{g.user_id}/media", **p)["id"])
    for f, video in zip(filhos, ehvideo):
        if video:
            g.aguardar(f)
    c = g.chamar("POST", f"{g.user_id}/media", media_type="CAROUSEL", children=",".join(filhos), caption=legenda)["id"]
    g.aguardar(c)
    return c


def publicar_item(item: Path, agora_mesmo=False, simular=False):
    post = fila.ler(item)
    if post["status"] == "publicado":
        print(f"já publicado: {post.get('resultado', {}).get('permalink')}")
        return True
    if post["status"] != "aprovado" or not post.get("aprovacao"):
        print(f"✗ {item.name}: status '{post['status']}' — só se publica item aprovado por um humano")
        return False
    if fila.impressao(item, post) != post["aprovacao"]["impressao"]:
        print(f"✗ {item.name}: mídia, legenda ou horário mudaram depois da aprovação — precisa de nova aprovação")
        return False
    if post["agendado_para"] and not agora_mesmo:
        quando = datetime.fromisoformat(post["agendado_para"])
        if quando > datetime.now(timezone.utc):
            print(f"· {item.name}: agendado para {post['agendado_para']} — ainda não")
            return True

    g = Graph(post["cliente"], simular)
    try:
        usado, total = g.cota()
        if usado >= total:
            raise RuntimeError(f"cota de publicação esgotada ({usado}/{total} nas últimas 24 h)")
        print(f"publicando {item.name} ({post['tipo']}, {len(post['midias'])} mídia(s)) · cota {usado}/{total}")
        prefixo = f"{post['cliente']}/{item.name}"
        urls = [hospedar.subir(item / m, f"{prefixo}/{Path(m).name}", simular) for m in post["midias"]]
        url_capa = hospedar.subir(item / post["capa"], f"{prefixo}/capa{Path(post['capa']).suffix}", simular) \
            if post.get("capa") else None
        container = criar_containers(g, post, urls, url_capa)
        media_id = g.chamar("POST", f"{g.user_id}/media_publish", creation_id=container)["id"]
        info = g.chamar("GET", media_id, fields="permalink,timestamp")
    except RuntimeError as e:
        post["status"] = "erro" if not simular else post["status"]
        post["historico"].append({"em": fila.agora().isoformat(timespec="seconds"), "evento": f"erro: {e}"})
        if not simular:
            fila.gravar(item, post)
        print(f"✗ {item.name}: {e}")
        return False

    if simular:
        print(f"✓ simulação ok — nada foi publicado")
        return True
    post["status"] = "publicado"
    post["resultado"] = {"media_id": media_id, "permalink": info.get("permalink"),
                         "publicado_em": info.get("timestamp") or fila.agora().isoformat(timespec="seconds")}
    post["historico"].append({"em": fila.agora().isoformat(timespec="seconds"), "evento": "publicado"})
    fila.gravar(item, post)
    hospedar.limpar(prefixo)
    print(f"✓ publicado: {post['resultado']['permalink']}")
    return True


METRICAS = {
    "reel": "reach,likes,comments,saved,shares,total_interactions,views",
    "feed": "reach,likes,comments,saved,shares,total_interactions,views",
    "carrossel": "reach,likes,comments,saved,shares,total_interactions,views",
    "story": "reach,replies,navigation,shares,total_interactions,views",
}


def metricas(item: Path, simular=False):
    post = fila.ler(item)
    if post["status"] != "publicado":
        sys.exit("só há métricas de item publicado")
    g = Graph(post["cliente"], simular)
    try:
        d = g.chamar("GET", f"{post['resultado']['media_id']}/insights", metric=METRICAS[post["tipo"]])
    except RuntimeError as e:
        sys.exit(f"insights indisponíveis: {e}\n(os nomes das métricas mudam entre versões da API — ajuste METRICAS)")
    valores = {m["name"]: (m.get("values") or [{}])[0].get("value", m.get("total_value", {}).get("value"))
               for m in d.get("data", [])}
    post.setdefault("metricas", []).append({"coletado_em": fila.agora().isoformat(timespec="seconds"), **valores})
    if not simular:
        fila.gravar(item, post)
    print(json.dumps(valores, ensure_ascii=False, indent=2))


def main():
    carregar_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simular", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("item"); i.add_argument("item"); i.add_argument("--agora", action="store_true")
    v = sub.add_parser("vencidos"); v.add_argument("--cliente")
    m = sub.add_parser("metricas"); m.add_argument("item")
    c = sub.add_parser("conta"); c.add_argument("--cliente", required=True)
    a = ap.parse_args()

    if a.cmd == "item":
        sys.exit(0 if publicar_item(Path(a.item), a.agora, a.simular) else 1)
    if a.cmd == "vencidos":
        ok = True
        for pj in sorted((fila.RAIZ / "clientes").glob(f"{a.cliente or '*'}/fila/*/post.json")):
            if json.loads(pj.read_text(encoding="utf-8"))["status"] == "aprovado":
                ok &= publicar_item(pj.parent, False, a.simular)
        sys.exit(0 if ok else 1)
    if a.cmd == "metricas":
        metricas(Path(a.item), a.simular)
    if a.cmd == "conta":
        g = Graph(a.cliente, a.simular)
        d = g.chamar("GET", g.user_id, fields="username,account_type,followers_count,media_count")
        usado, total = g.cota()
        print(f"@{d.get('username', a.cliente)} · {d.get('account_type', '?')} · "
              f"{d.get('followers_count', '?')} seguidores · cota {usado}/{total} nas últimas 24 h")


if __name__ == "__main__":
    main()
