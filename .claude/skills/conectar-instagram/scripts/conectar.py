#!/usr/bin/env python3
"""Conecta a conta do Instagram de um cliente pelo login oficial (OAuth) e
guarda o token no .env — o token nunca é impresso.

Uso:
    python conectar.py url      --cliente <handle>              # 1. gera o link de autorização
    python conectar.py trocar   --cliente <handle> --retorno "<URL completa para onde o Instagram redirecionou>"
    python conectar.py status   [--cliente <handle>]            # quem está conectado e quando o token vence
    python conectar.py renovar  --cliente <handle>              # renova o token de 60 dias
    python conectar.py desconectar --cliente <handle>           # apaga o token do .env

Fluxo:
    1. `url` imprime o link. Quem abre é o DONO da conta (ou alguém com acesso a ela),
       no navegador dele. Ele faz login no Instagram e autoriza as permissões.
    2. O Instagram redireciona para IG_REDIRECT_URI com ?code=...&state=...
       A página pode até dar erro — o que importa é a URL na barra de endereço.
    3. `trocar` recebe essa URL, confere o `state` (proteção contra CSRF), troca o
       código por token de longa duração (60 dias) e confere que a conta conectada
       é mesmo o @ do cliente. Conta errada é recusada.

Permissões pedidas:
    instagram_business_basic              perfil e mídia
    instagram_business_manage_insights    alcance, salvamentos, compartilhamentos, views
    instagram_business_content_publish    publicar (usado pela skill publicar-instagram)

App da Meta no .env: IG_APP_ID, IG_APP_SECRET, IG_REDIRECT_URI (HTTPS, cadastrada no app).
"""

import argparse
import json
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ig_api  # noqa: E402

ESCOPOS = ["instagram_business_basic", "instagram_business_manage_insights",
           "instagram_business_content_publish"]
VALIDADE_STATE_S = 15 * 60


def app():
    faltando = [k for k in ("IG_APP_ID", "IG_APP_SECRET", "IG_REDIRECT_URI") if not ig_api.os.environ.get(k)]
    if faltando:
        sys.exit(f"app da Meta não configurado no .env: {', '.join(faltando)} "
                 "(veja references/conectar.md)")
    env = ig_api.os.environ
    if not env["IG_REDIRECT_URI"].startswith("https://"):
        sys.exit("IG_REDIRECT_URI precisa ser HTTPS e estar cadastrada no app da Meta")
    return env["IG_APP_ID"], env["IG_APP_SECRET"], env["IG_REDIRECT_URI"]


def arq_state(handle):
    return ig_api.RAIZ / "clientes" / handle / ".oauth-state.json"


def cmd_url(a):
    app_id, _, redirect = app()
    state = secrets.token_urlsafe(24)
    arq = arq_state(a.cliente)
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps({"state": state, "criado_em": time.time()}), encoding="utf-8")
    arq.chmod(0o600)
    url = "https://www.instagram.com/oauth/authorize?" + urlencode({
        "client_id": app_id, "redirect_uri": redirect, "response_type": "code",
        "scope": ",".join(ESCOPOS), "state": state, "force_authentication": 1, "enable_fb_login": 0,
    })
    print("Envie este link ao dono da conta @" + a.cliente + " (vale por 15 minutos):\n")
    print(url)
    print("\nDepois de autorizar, ele copia a URL completa da barra de endereço e te devolve.")


def cmd_trocar(a):
    import requests
    app_id, app_secret, redirect = app()
    q = parse_qs(urlparse(a.retorno.strip()).query)
    if "error" in q:
        sys.exit(f"autorização negada: {q.get('error_description', q['error'])[0]}")
    code = (q.get("code") or [None])[0]
    state = (q.get("state") or [None])[0]
    arq = arq_state(a.cliente)
    if not arq.exists():
        sys.exit("nenhum link pendente para este cliente — gere com `conectar.py url`")
    salvo = json.loads(arq.read_text(encoding="utf-8"))
    if not state or not secrets.compare_digest(state, salvo["state"]):
        sys.exit("state não confere — o link não foi gerado aqui para este cliente. Gere outro.")
    if time.time() - salvo["criado_em"] > VALIDADE_STATE_S:
        sys.exit("link expirado (15 min) — gere outro com `conectar.py url`")
    if not code:
        sys.exit("URL sem ?code= — confira se copiou a URL inteira")
    code = code.split("#")[0]

    r = requests.post("https://api.instagram.com/oauth/access_token", data={
        "client_id": app_id, "client_secret": app_secret, "grant_type": "authorization_code",
        "redirect_uri": redirect, "code": code}, timeout=60)
    dados = r.json()
    if r.status_code >= 400:
        sys.exit(f"troca do código falhou: {dados.get('error_message') or dados}")
    dados = dados.get("data", [dados])[0]
    curto, user_id = dados["access_token"], str(dados["user_id"])
    permitidas = set(dados.get("permissions", "").split(",")) if isinstance(dados.get("permissions"), str) \
        else set(dados.get("permissions") or [])

    r = requests.get("https://graph.instagram.com/access_token", params={
        "grant_type": "ig_exchange_token", "client_secret": app_secret, "access_token": curto}, timeout=60)
    longo = r.json()
    if r.status_code >= 400:
        sys.exit(f"token de longa duração falhou: {longo}")
    token, expira_s = longo["access_token"], int(longo.get("expires_in", 5184000))

    r = requests.get(f"https://graph.instagram.com/{ig_api.versao()}/me",
                     params={"fields": "user_id,username,account_type", "access_token": token}, timeout=60)
    me = r.json()
    username = me.get("username", "")
    if username.lower() != a.cliente.lower():
        sys.exit(f"a conta autorizada é @{username}, não @{a.cliente} — nada foi gravado. "
                 "Peça ao dono da conta certa para autorizar.")

    k = ig_api.chave(a.cliente)
    expira = datetime.now(timezone.utc) + timedelta(seconds=expira_s)
    ig_api.gravar_env({
        f"IG_{k}_USER_ID": me.get("user_id") or user_id,
        f"IG_{k}_TOKEN": token,
        f"IG_{k}_TOKEN_EXPIRA": expira.isoformat(timespec="seconds"),
        f"IG_{k}_GRAPH_HOST": "graph.instagram.com",
    })
    arq.unlink()
    conta = ig_api.RAIZ / "clientes" / a.cliente / "conta.json"
    conta.write_text(json.dumps({
        "username": username, "user_id": me.get("user_id") or user_id, "tipo": me.get("account_type"),
        "conectado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "token_expira": expira.isoformat(timespec="seconds"),
        "permissoes": sorted(permitidas) or ESCOPOS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    faltam = [e for e in ESCOPOS if permitidas and e not in permitidas]
    print(f"✓ @{username} conectado ({me.get('account_type')}) · token válido até {expira:%d/%m/%Y}")
    if faltam:
        print(f"! permissões não concedidas: {', '.join(faltam)} — o que depende delas vai falhar")


def cmd_status(a):
    handles = [a.cliente] if a.cliente else sorted(
        p.parent.name for p in (ig_api.RAIZ / "clientes").glob("*/conta.json"))
    if not handles:
        print("nenhuma conta conectada")
    for h in handles:
        k = ig_api.chave(h)
        expira = ig_api.os.environ.get(f"IG_{k}_TOKEN_EXPIRA")
        if not ig_api.os.environ.get(f"IG_{k}_TOKEN"):
            print(f"@{h}: não conectado")
            continue
        dias = (datetime.fromisoformat(expira) - datetime.now(timezone.utc)).days if expira else None
        aviso = " — RENOVE JÁ" if dias is not None and dias < 10 else ""
        print(f"@{h}: conectado · token vence em {dias if dias is not None else '?'} dia(s){aviso}")


def cmd_renovar(a):
    import requests
    conta = ig_api.Conta(a.cliente)
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": conta.token}, timeout=60)
    d = r.json()
    if r.status_code >= 400:
        sys.exit(f"renovação falhou: {d} — se o token já venceu, conecte de novo")
    expira = datetime.now(timezone.utc) + timedelta(seconds=int(d.get("expires_in", 5184000)))
    k = ig_api.chave(a.cliente)
    ig_api.gravar_env({f"IG_{k}_TOKEN": d["access_token"], f"IG_{k}_TOKEN_EXPIRA": expira.isoformat(timespec="seconds")})
    print(f"✓ token de @{a.cliente} renovado até {expira:%d/%m/%Y}")


def cmd_desconectar(a):
    k = ig_api.chave(a.cliente)
    ig_api.gravar_env({f"IG_{k}_TOKEN": "", f"IG_{k}_TOKEN_EXPIRA": ""})
    conta = ig_api.RAIZ / "clientes" / a.cliente / "conta.json"
    if conta.exists():
        conta.unlink()
    print(f"@{a.cliente} desconectado. Para revogar do lado da Meta: Instagram → Configurações → "
          "Apps e sites → remover o app.")


def main():
    ig_api.carregar_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("url", "trocar", "renovar", "desconectar"):
        p = sub.add_parser(nome)
        p.add_argument("--cliente", required=True)
        if nome == "trocar":
            p.add_argument("--retorno", required=True, help="URL completa do redirecionamento")
    s = sub.add_parser("status")
    s.add_argument("--cliente")
    a = ap.parse_args()
    {"url": cmd_url, "trocar": cmd_trocar, "status": cmd_status,
     "renovar": cmd_renovar, "desconectar": cmd_desconectar}[a.cmd](a)


if __name__ == "__main__":
    main()
