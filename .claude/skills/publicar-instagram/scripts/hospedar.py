#!/usr/bin/env python3
"""Hospedagem temporária da mídia para a Graph API buscar.

A API do Instagram não recebe upload de arquivo: ela baixa a mídia de uma URL
pública. Este módulo sobe o arquivo para um bucket PRIVADO do Supabase Storage
e devolve uma URL assinada que expira em 1 hora — tempo de sobra para a Meta
baixar, sem deixar o criativo exposto antes da publicação.

Configuração (.env):
    SUPABASE_URL=https://<projeto>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=...        # chave de serviço: só no servidor, nunca no front
    SUPABASE_BUCKET=instagram-fila       # bucket privado (criar uma vez)

Uso direto (teste):
    python hospedar.py arquivo.jpg cliente/item/01.jpg
"""

import mimetypes
import os
import sys
from pathlib import Path
from urllib.parse import quote

EXPIRA_S = 3600


def _config():
    url, chave = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    bucket = os.environ.get("SUPABASE_BUCKET", "instagram-fila")
    if not (url and chave):
        sys.exit("hospedagem não configurada: defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no .env "
                 "(veja references/configuracao-meta.md, seção Hospedagem)")
    return url.rstrip("/"), chave, bucket


def subir(arquivo: Path, destino: str, simular=False) -> str:
    if simular:
        return f"https://<supabase>/storage/v1/object/sign/<bucket>/{destino}?token=<simulado>"
    import requests
    url, chave, bucket = _config()
    cab = {"Authorization": f"Bearer {chave}", "apikey": chave}
    tipo = mimetypes.guess_type(arquivo.name)[0] or "application/octet-stream"
    caminho = quote(destino)
    with open(arquivo, "rb") as f:
        r = requests.post(f"{url}/storage/v1/object/{bucket}/{caminho}", data=f,
                          headers={**cab, "Content-Type": tipo, "x-upsert": "true"}, timeout=300)
    if r.status_code >= 400:
        raise RuntimeError(f"upload falhou ({r.status_code}): {r.text[:300]}")
    r = requests.post(f"{url}/storage/v1/object/sign/{bucket}/{caminho}", json={"expiresIn": EXPIRA_S},
                      headers=cab, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"URL assinada falhou ({r.status_code}): {r.text[:300]}")
    assinada = r.json().get("signedURL") or r.json().get("signedUrl")
    return f"{url}/storage/v1{assinada}" if assinada.startswith("/") else assinada


def limpar(prefixo: str):
    """Apaga a mídia hospedada depois da publicação (a Meta já copiou)."""
    if not os.environ.get("SUPABASE_URL"):
        return
    import requests
    url, chave, bucket = _config()
    cab = {"Authorization": f"Bearer {chave}", "apikey": chave}
    r = requests.post(f"{url}/storage/v1/object/list/{bucket}", json={"prefix": prefixo, "limit": 100},
                      headers=cab, timeout=60)
    if r.status_code < 400:
        nomes = [f"{prefixo}/{o['name']}" for o in r.json()]
        if nomes:
            requests.delete(f"{url}/storage/v1/object/{bucket}", json={"prefixes": nomes}, headers=cab, timeout=60)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(subir(Path(sys.argv[1]), sys.argv[2]))
