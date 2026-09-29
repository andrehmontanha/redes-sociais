"""Acesso comum à Instagram API (login do Instagram) para os scripts do estúdio.

Credenciais por cliente no .env da raiz (gravadas pelo conectar.py):
    IG_<HANDLE>_USER_ID, IG_<HANDLE>_TOKEN, IG_<HANDLE>_TOKEN_EXPIRA, IG_<HANDLE>_GRAPH_HOST
App da Meta (uma vez por estúdio):
    IG_APP_ID, IG_APP_SECRET, IG_REDIRECT_URI, IG_GRAPH_VERSION
"""

import os
import re
import sys
import time
from pathlib import Path

RAIZ = Path(os.environ.get("ESTUDIO_RAIZ", Path(__file__).resolve().parents[4]))
ENV = RAIZ / ".env"


def carregar_env():
    if ENV.exists():
        for linha in ENV.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def chave(handle):
    return re.sub(r"[^A-Z0-9]", "_", handle.upper())


def gravar_env(valores: dict):
    """Atualiza chaves no .env sem mexer no resto e sem imprimir valores."""
    linhas = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    restantes = dict(valores)
    novas = []
    for linha in linhas:
        k = linha.split("=", 1)[0].strip() if "=" in linha and not linha.lstrip().startswith("#") else None
        if k in restantes:
            novas.append(f"{k}={restantes.pop(k)}")
        else:
            novas.append(linha)
    novas += [f"{k}={v}" for k, v in restantes.items()]
    ENV.write_text("\n".join(novas) + "\n", encoding="utf-8")
    os.chmod(ENV, 0o600)
    for k, v in valores.items():
        os.environ[k] = str(v)


def versao():
    return os.environ.get("IG_GRAPH_VERSION", "v23.0")


class Conta:
    """Chamadas autenticadas em nome da conta conectada de um cliente."""

    def __init__(self, handle):
        k = chave(handle)
        self.handle = handle
        self.user_id = os.environ.get(f"IG_{k}_USER_ID")
        self.token = os.environ.get(f"IG_{k}_TOKEN")
        host = os.environ.get(f"IG_{k}_GRAPH_HOST") or os.environ.get("IG_GRAPH_HOST", "graph.instagram.com")
        self.base = f"https://{host}/{versao()}"
        if not (self.user_id and self.token):
            sys.exit(f"@{handle} não está conectado — rode conectar.py url --cliente {handle}")

    def get(self, caminho, **params):
        import requests
        params["access_token"] = self.token
        url = caminho if caminho.startswith("http") else f"{self.base}/{caminho}"
        for tentativa in range(4):
            r = requests.get(url, params=params if not caminho.startswith("http") else None, timeout=60)
            if r.status_code not in (429, 500, 502, 503, 504):
                break
            time.sleep(2 ** (tentativa + 1))
        dados = r.json() if "json" in r.headers.get("content-type", "") else {}
        if r.status_code >= 400 or "error" in dados:
            erro = dados.get("error", {})
            raise RuntimeError(f"{r.status_code} em {caminho.split('?')[0]}: {erro.get('message', r.text[:200])} "
                               f"(code {erro.get('code')})")
        return dados

    def paginas(self, caminho, limite=None, **params):
        """Itera sobre todos os itens de um endpoint paginado."""
        dados = self.get(caminho, **params)
        vistos = 0
        while True:
            for item in dados.get("data", []):
                yield item
                vistos += 1
                if limite and vistos >= limite:
                    return
            proxima = dados.get("paging", {}).get("next")
            if not proxima:
                return
            dados = self.get(proxima)
