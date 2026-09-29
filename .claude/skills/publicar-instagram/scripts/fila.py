#!/usr/bin/env python3
"""Fila de publicação com trava de aprovação humana.

Uso:
    python fila.py criar --cliente <handle> --tipo carrossel \\
        --midias clientes/<h>/criativos/<id>/render/*.jpg \\
        --legenda-arquivo clientes/<h>/criativos/<id>/legenda.txt \\
        --agendar 2026-10-02T18:00-03:00 [--capa capa.jpg] [--thumb-offset-ms 1000]
    python fila.py previa   clientes/<h>/fila/<item>
    python fila.py aprovar  clientes/<h>/fila/<item> --por "Nome de quem aprovou"
    python fila.py rejeitar clientes/<h>/fila/<item> --motivo "trocar a foto da capa"
    python fila.py listar [--cliente <handle>] [--status aguardando_aprovacao]

Estados: rascunho → aguardando_aprovacao → aprovado → publicado
                                         ↘ rejeitado        ↘ erro
                                         ↘ cancelado (consentimento de avatar revogado)

A trava: ao criar, a mídia é COPIADA para dentro do item (congelada) e o item
ganha uma impressão digital — sha256 da mídia, da legenda, do tipo e do horário.
`aprovar` grava essa impressão; `publicar.py` recalcula e recusa se qualquer
byte mudou. Mudou a legenda depois do "ok"? Precisa de novo "ok".

`aprovar` registra uma decisão HUMANA. O agente só roda esse comando depois de
uma mensagem explícita de aprovação do usuário, com o nome de quem aprovou —
nunca por conta própria, nunca por inferência.
"""

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# raiz do estúdio (onde fica clientes/); ESTUDIO_RAIZ sobrescreve, útil em testes
RAIZ = Path(os.environ.get("ESTUDIO_RAIZ", Path(__file__).resolve().parents[4]))
TIPOS = {"feed": (1, 1), "carrossel": (2, 10), "reel": (1, 1), "story": (1, 1)}
IMG = {".jpg", ".jpeg"}
VID = {".mp4", ".mov"}


def agora():
    return datetime.now(timezone.utc).astimezone()


def ler(item: Path):
    return json.loads((item / "post.json").read_text(encoding="utf-8"))


def gravar(item: Path, post):
    (item / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2), encoding="utf-8")


def sha(arq: Path):
    h = hashlib.sha256()
    with open(arq, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def impressao(item: Path, post):
    h = hashlib.sha256()
    for m in post["midias"] + ([post["capa"]] if post.get("capa") else []):
        h.update(sha(item / m).encode())
    for campo in ("tipo", "legenda", "agendado_para", "thumb_offset_ms", "avatares"):
        h.update(f"{campo}={post.get(campo)}".encode())
    return h.hexdigest()


def validar_legenda(legenda):
    erros = []
    if len(legenda) > 2200:
        erros.append(f"legenda com {len(legenda)} caracteres (máx. 2200)")
    if len(re.findall(r"(?<!\w)#\w+", legenda)) > 30:
        erros.append("mais de 30 hashtags")
    if len(re.findall(r"(?<!\w)@[\w.]+", legenda)) > 20:
        erros.append("mais de 20 menções")
    return erros


AVISO_IA = "Vídeo com avatar digital criado com IA, com autorização da pessoa retratada."


def avatares_da_midia(midias):
    """Pessoas cujos avatares aparecem na mídia: `avatares.json` ao lado do arquivo
    (gerado pelo montar_reel.py) ou o manifesto `.json` do próprio vídeo de avatar."""
    pessoas = set()
    for m in midias:
        for candidato in (m.parent / "avatares.json", m.with_suffix(".json")):
            if candidato.exists():
                dados = json.loads(candidato.read_text(encoding="utf-8"))
                if isinstance(dados, dict) and dados.get("pessoa"):
                    pessoas.add(dados["pessoa"])
                elif isinstance(dados, dict) and isinstance(dados.get("avatares"), list):
                    pessoas.update(dados["avatares"])
    return sorted(pessoas)


def verificador_avatares():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "avatares" / "scripts"))
    import avatar
    avatar.RAIZ = RAIZ
    return avatar


def criar(a):
    tipo = a.tipo
    minimo, maximo = TIPOS[tipo]
    midias = [Path(m) for m in a.midias]
    if not minimo <= len(midias) <= maximo:
        sys.exit(f"{tipo}: de {minimo} a {maximo} mídia(s), recebi {len(midias)}")
    for m in midias:
        if not m.exists():
            sys.exit(f"mídia não encontrada: {m}")
        ext = m.suffix.lower()
        if tipo == "reel" and ext not in VID:
            sys.exit(f"reel precisa de vídeo .mp4/.mov: {m}")
        if tipo == "feed" and ext not in IMG:
            sys.exit(f"feed precisa de imagem JPEG (vídeo vai como reel; PNG não é aceito pela API): {m}")
        if ext not in IMG | VID:
            sys.exit(f"formato não aceito pela API: {m} (use JPEG ou MP4)")

    legenda = ""
    if a.legenda_arquivo:
        legenda = Path(a.legenda_arquivo).read_text(encoding="utf-8").strip()
    elif a.legenda:
        legenda = a.legenda.strip()
    if tipo == "story" and legenda:
        sys.exit("story não tem legenda na API — deixe o texto na própria arte")
    for m in midias:  # créditos exigidos por som CC-BY (gerados pelo mixar_sfx.py)
        cred = m.with_suffix(".creditos.txt")
        if cred.exists():
            legenda = (legenda + "\n\n" + cred.read_text(encoding="utf-8").strip()).strip()
    pessoas = sorted(set(avatares_da_midia(midias)) | set(filter(None, (a.avatares or "").split(","))))
    if pessoas:
        av = verificador_avatares()
        impedimentos = [e for p in pessoas for e in av.verificar_uso(a.cliente, p)]
        if impedimentos:
            sys.exit("avatar sem liberação:\n  " + "\n  ".join(impedimentos))
        if AVISO_IA.lower() not in legenda.lower():
            legenda = (legenda + "\n\n" + AVISO_IA).strip()
    erros = validar_legenda(legenda)
    if erros:
        sys.exit("legenda inválida: " + "; ".join(erros))

    agendado = datetime.fromisoformat(a.agendar) if a.agendar else None
    if agendado and agendado.tzinfo is None:
        sys.exit("--agendar precisa de fuso horário, ex.: 2026-10-02T18:00-03:00")

    carimbo = agora().strftime("%Y%m%d-%H%M%S")
    item = RAIZ / "clientes" / a.cliente / "fila" / f"{carimbo}-{tipo}"
    (item / "midia").mkdir(parents=True)
    copias = []
    for i, m in enumerate(midias, 1):
        destino = item / "midia" / f"{i:02d}{m.suffix.lower()}"
        shutil.copy2(m, destino)
        copias.append(str(destino.relative_to(item)))
    capa = None
    if a.capa:
        capa_dest = item / "midia" / f"capa{Path(a.capa).suffix.lower()}"
        shutil.copy2(a.capa, capa_dest)
        capa = str(capa_dest.relative_to(item))

    post = {
        "cliente": a.cliente,
        "tipo": tipo,
        "status": "rascunho",
        "criado_em": agora().isoformat(timespec="seconds"),
        "origem": [str(m) for m in midias],
        "midias": copias,
        "capa": capa,
        "thumb_offset_ms": a.thumb_offset_ms,
        "legenda": legenda,
        "agendado_para": agendado.isoformat() if agendado else None,
        "aprovacao": None,
        "avatares": pessoas,
        "historico": [{"em": agora().isoformat(timespec="seconds"), "evento": "criado"}],
    }
    gravar(item, post)
    print(item)


def previa(a):
    item = Path(a.item)
    post = ler(item)
    if post["status"] not in ("rascunho", "rejeitado", "aguardando_aprovacao"):
        sys.exit(f"item em '{post['status']}' — prévia só antes da aprovação")
    cartoes = []
    for m in post["midias"]:
        if Path(m).suffix.lower() in VID:
            cartoes.append(f'<video src="{m}" controls playsinline muted></video>')
        else:
            cartoes.append(f'<img src="{m}" alt="">')
    capa = f'<p class="nota">Capa na grade:</p><img class="capa" src="{post["capa"]}" alt="">' if post.get("capa") else ""
    quando = post["agendado_para"] or "assim que aprovado"
    doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Prévia · @{html.escape(post['cliente'])}</title>
<style>
:root{{--fundo:#fafafa;--cartao:#fff;--texto:#111;--suave:#666;--borda:#e5e5e5;--acento:#0a66c2}}
@media (prefers-color-scheme:dark){{:root{{--fundo:#111;--cartao:#1b1b1b;--texto:#eee;--suave:#aaa;--borda:#333}}}}
body{{margin:0;background:var(--fundo);color:var(--texto);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:480px;margin:0 auto;padding:16px}}
.cabeca{{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}}
.selo{{font-size:13px;padding:2px 10px;border-radius:99px;background:#fff3cd;color:#664d03}}
.midias{{display:flex;gap:8px;overflow-x:auto;scroll-snap-type:x mandatory;border:1px solid var(--borda);border-radius:8px;background:var(--cartao)}}
.midias img,.midias video{{width:100%;flex:0 0 100%;scroll-snap-align:start;display:block}}
.legenda{{white-space:pre-wrap;background:var(--cartao);border:1px solid var(--borda);border-radius:8px;padding:12px;margin-top:12px}}
.nota{{color:var(--suave);font-size:14px}} .capa{{width:40%;border-radius:6px}}
dl{{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:14px}} dt{{color:var(--suave)}}
</style></head><body><main>
<div class="cabeca"><h1 style="font-size:20px;margin:0">@{html.escape(post['cliente'])} · {post['tipo']}</h1>
<span class="selo">aguardando aprovação</span></div>
{f'<p class="selo" style="background:#e7f1ff;color:#0a3d7a;display:inline-block">contém avatar digital criado com IA: {html.escape(", ".join(post["avatares"]))}</p>' if post.get("avatares") else ""}
<dl><dt>Publicação</dt><dd>{html.escape(quando)}</dd><dt>Peças</dt><dd>{len(post['midias'])}</dd>
<dt>Item</dt><dd>{html.escape(item.name)}</dd></dl>
<div class="midias">{''.join(cartoes)}</div>
{f'<p class="nota">Arraste para ver as {len(cartoes)} peças.</p>' if len(cartoes) > 1 else ''}
<div class="legenda">{html.escape(post['legenda']) or '<span class="nota">sem legenda</span>'}</div>
{capa}
<p class="nota">Para aprovar, responda com "aprovado" e seu nome. Para ajustar, diga o que mudar.</p>
</main></body></html>"""
    (item / "previa.html").write_text(doc, encoding="utf-8")
    if post["status"] != "aguardando_aprovacao":
        post["status"] = "aguardando_aprovacao"
        post["historico"].append({"em": agora().isoformat(timespec="seconds"), "evento": "prévia enviada"})
        gravar(item, post)
    print(item / "previa.html")


def aprovar(a):
    item = Path(a.item)
    post = ler(item)
    if post["status"] != "aguardando_aprovacao":
        sys.exit(f"item em '{post['status']}' — só se aprova o que teve prévia enviada")
    if len(a.por.strip()) < 2:
        sys.exit("--por precisa do nome de quem aprovou")
    pessoas_ok = {p.strip().lower() for p in (a.pessoas or "").split(",") if p.strip()}
    if post.get("avatares"):
        av = verificador_avatares()
        for p in post["avatares"]:
            impedimentos = av.verificar_uso(post["cliente"], p)
            if impedimentos:
                sys.exit("avatar sem liberação:\n  " + "\n  ".join(impedimentos))
            reg = av.ler(post["cliente"], p)
            if reg["termo"]["exige_aprovacao_da_pessoa"] and reg["pessoa"]["nome"].lower() not in pessoas_ok:
                sys.exit(f"o termo de {reg['pessoa']['nome']} exige que a própria pessoa aprove cada post — "
                         f"mostre a prévia e registre com --pessoas \"{reg['pessoa']['nome']}\"")
    post["aprovacao"] = {"por": a.por.strip(), "em": agora().isoformat(timespec="seconds"),
                         "impressao": impressao(item, post), "mensagem": a.mensagem,
                         "pessoas_retratadas": sorted(pessoas_ok) or None}
    post["status"] = "aprovado"
    post["historico"].append({"em": post["aprovacao"]["em"], "evento": f"aprovado por {a.por.strip()}"})
    gravar(item, post)
    print(f"aprovado por {a.por.strip()} · publica em {post['agendado_para'] or 'imediato'}")


def rejeitar(a):
    item = Path(a.item)
    post = ler(item)
    if post["status"] in ("publicado",):
        sys.exit("item já publicado")
    post["status"] = "rejeitado"
    post["aprovacao"] = None
    post["historico"].append({"em": agora().isoformat(timespec="seconds"), "evento": f"rejeitado: {a.motivo}"})
    gravar(item, post)
    print(f"rejeitado — {a.motivo}")


def listar(a):
    base = RAIZ / "clientes"
    for pj in sorted(base.glob(f"{a.cliente or '*'}/fila/*/post.json")):
        post = json.loads(pj.read_text(encoding="utf-8"))
        if a.status and post["status"] != a.status:
            continue
        print(f"{post['status']:22s} {post['cliente']:24s} {post['tipo']:9s} "
              f"{(post['agendado_para'] or '-'):26s} {pj.parent.relative_to(RAIZ)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("criar")
    c.add_argument("--cliente", required=True)
    c.add_argument("--tipo", choices=list(TIPOS), required=True)
    c.add_argument("--midias", nargs="+", required=True)
    c.add_argument("--legenda-arquivo")
    c.add_argument("--legenda")
    c.add_argument("--agendar", help="ISO 8601 com fuso, ex. 2026-10-02T18:00-03:00")
    c.add_argument("--capa")
    c.add_argument("--thumb-offset-ms", type=int)
    c.add_argument("--avatares", help="slugs de avatares presentes (detectados sozinhos quando há avatares.json)")
    p = sub.add_parser("previa"); p.add_argument("item")
    ap_ = sub.add_parser("aprovar"); ap_.add_argument("item"); ap_.add_argument("--por", required=True)
    ap_.add_argument("--mensagem", help="texto da mensagem de aprovação do usuário, para o registro")
    ap_.add_argument("--pessoas", help="nomes das pessoas retratadas por avatar que aprovaram (separados por vírgula)")
    r = sub.add_parser("rejeitar"); r.add_argument("item"); r.add_argument("--motivo", required=True)
    l = sub.add_parser("listar"); l.add_argument("--cliente"); l.add_argument("--status")
    a = ap.parse_args()
    {"criar": criar, "previa": previa, "aprovar": aprovar, "rejeitar": rejeitar, "listar": listar}[a.cmd](a)


if __name__ == "__main__":
    main()
