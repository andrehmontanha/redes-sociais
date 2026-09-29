#!/usr/bin/env python3
"""Monta o moodboard HTML autocontido a partir da pasta de assets.

Uso:
    python montar_moodboard.py assets/ --saida moodboard.html \
        --handle thermasdeolimpiaresort --titulo "Referência visual"

Lê o inventario.csv, embute as miniaturas como data URI (a página abre sozinha
em qualquer lugar, sem depender dos arquivos ao lado) e agrupa por origem,
repetindo o aviso de uso em cada bloco.

O moodboard não é galeria: é argumento. Cada bloco aceita uma legenda dizendo o
que observar ali. Preencha via --notas notas.json:
    {"concorrentes": "Repare na tipografia pesada nas capas...", "cliente": "..."}
"""

import argparse
import base64
import csv
import html
import io
import json
from datetime import date
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}

ORDEM = ["cliente", "criadores", "concorrentes", "bancos", "indefinida"]

ROTULO = {
    "cliente": "Material do cliente",
    "criadores": "Criadores e UGC",
    "concorrentes": "Concorrentes",
    "bancos": "Bancos livres",
    "indefinida": "Origem não classificada",
}

CLASSE_USO = {
    "cliente": "ok",
    "criadores": "warn",
    "concorrentes": "bad",
    "bancos": "ok",
    "indefinida": "warn",
}


def miniatura(caminho: Path, largura: int = 460) -> str:
    """Devolve um data URI da miniatura, ou string vazia se não der."""
    if Image is None or caminho.suffix.lower() not in IMG_EXT or not caminho.exists():
        return ""
    try:
        with Image.open(caminho) as im:
            im = im.convert("RGB")
            if im.width > largura:
                im = im.resize((largura, round(im.height * largura / im.width)),
                               Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=72, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def colapsar_variantes(itens: list) -> list:
    """Reduz as variantes de exportação a um item por asset.

    O inventário lista cada arquivo, e cada foto vira 6 arquivos (3 larguras ×
    webp/jpg). Mostrar todos transforma um moodboard de 4 fotos em 24 tiles de
    ruído. Aqui `foto-400.webp`, `foto-800.jpg`… viram um tile só, e o vídeo
    absorve seu poster como miniatura.
    """
    import re
    grupos, ordem = {}, []
    for it in itens:
        cam = Path(it["arquivo"])
        base = cam.stem
        m = re.match(r"^(.*)-(\d{3,4})$", base)          # foto-1600
        if m:
            base, largura = m.group(1), int(m.group(2))
        else:
            largura = None
        base = re.sub(r"-poster$", "", base)             # video-poster -> video
        # `originais/` e `web/` guardam o MESMO asset em estágios diferentes do
        # pipeline. Para o moodboard isso é um asset só — quem olha quer ver a
        # foto, não o processo de exportação.
        pasta = cam.parent
        if pasta.name in {"originais", "web"}:
            pasta = pasta.parent
        chave = str(pasta / base)

        if chave not in grupos:
            grupos[chave] = {**it, "_variantes": set(), "_larguras": set(),
                             "_peso": 0, "_thumb": None, "_maior": -1}
            ordem.append(chave)
        g = grupos[chave]
        g["_peso"] += int(it.get("peso_kb") or 0)
        if largura:
            g["_larguras"].add(largura)
        g["_variantes"].add(cam.suffix.lstrip(".").lower())

        # Miniatura: a maior imagem disponível do grupo (o poster serve ao vídeo).
        if cam.suffix.lower() in IMG_EXT:
            score = largura or int(it.get("largura") or 0)
            if score > g["_maior"]:
                g["_maior"], g["_thumb"] = score, it["arquivo"]
        if it.get("tipo") == "video":
            g["tipo"] = "video"

    saida = []
    for chave in ordem:
        g = grupos[chave]
        larguras = sorted(g["_larguras"])
        exts = sorted(g["_variantes"] - {"jpg"} if len(g["_variantes"]) > 1 else g["_variantes"])
        detalhe = []
        if larguras:
            detalhe.append(f"{len(larguras)} larguras até {max(larguras)}px")
        if len(g["_variantes"]) > 1:
            detalhe.append("+".join(sorted(g["_variantes"])))
        saida.append({
            **g,
            "arquivo": chave + ("" if g["tipo"] == "video" else ""),
            "nome": Path(chave).name,
            "thumb": g["_thumb"],
            "peso_kb": g["_peso"],
            "detalhe": " · ".join(detalhe) if detalhe else (
                f"{g.get('largura')}×{g.get('altura')}" if g.get("largura") else g.get("tipo", "")),
        })
    return saida


CSS = """
:root{--bg:#fbfaf9;--surface:#fff;--surface-2:#f5f2ef;--border:#e6e2dd;--text:#1c1a17;
  --muted:#6b6560;--accent:#0e7490;--ok:#15803d;--warn:#b45309;--bad:#b91c1c;
  --shadow:0 1px 2px rgba(0,0,0,.04),0 8px 24px rgba(0,0,0,.04);}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#141312;--surface:#1c1b19;--surface-2:#232120;--border:#2f2c29;--text:#f0ede9;
  --muted:#9c948c;--accent:#67e8f9;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.25);}}
:root[data-theme="dark"]{--bg:#141312;--surface:#1c1b19;--surface-2:#232120;
  --border:#2f2c29;--text:#f0ede9;--muted:#9c948c;--accent:#67e8f9;
  --ok:#4ade80;--warn:#fbbf24;--bad:#f87171;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:16px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:52px 24px 88px}
header{border-bottom:1px solid var(--border);padding-bottom:24px;margin-bottom:36px}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:650}
h1{font-size:clamp(26px,4vw,36px);margin:10px 0 6px;letter-spacing:-.02em}
.meta{color:var(--muted);font-size:14px}
h2{font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
  margin:48px 0 6px;font-weight:650}
.aviso{display:inline-block;font-size:12px;font-weight:650;padding:3px 10px;
  border-radius:999px;border:1px solid currentColor;margin-bottom:12px}
.aviso.ok{color:var(--ok)}.aviso.warn{color:var(--warn)}.aviso.bad{color:var(--bad)}
.nota{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:10px;padding:14px 18px;margin:0 0 18px;font-size:14px;color:var(--text)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;
  align-items:start}
.item{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  overflow:hidden;box-shadow:var(--shadow)}
.item .thumb{position:relative}
/* Vertical (Reel 9:16) ao lado de horizontal desalinha a grade inteira.
   `contain` limita a altura sem cortar o enquadramento — e enquadramento é
   justamente o que se olha num moodboard. */
.item img{display:block;width:100%;height:auto;max-height:360px;object-fit:contain;
  background:var(--surface-2)}
.item .selo{position:absolute;top:8px;left:8px;font-size:11px;font-weight:700;
  letter-spacing:.05em;text-transform:uppercase;padding:3px 8px;border-radius:999px;
  background:rgba(0,0,0,.62);color:#fff;backdrop-filter:blur(4px)}
.item .semimg{padding:40px 16px;text-align:center;color:var(--muted);font-size:13px;
  background:var(--surface-2)}
.item .cap{padding:10px 12px;font-size:12px;color:var(--muted);
  display:flex;justify-content:space-between;gap:8px;align-items:baseline}
.item .cap .n{color:var(--text);font-weight:600;word-break:break-word}
.vazio{color:var(--muted);font-size:14px;font-style:italic}
footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--border);
  font-size:13px;color:var(--muted)}
@media print{body{background:#fff}.item{box-shadow:none}}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raiz", type=Path)
    ap.add_argument("--saida", type=Path, default=Path("moodboard.html"))
    ap.add_argument("--handle", default="")
    ap.add_argument("--titulo", default="Referência visual")
    ap.add_argument("--notas", type=Path, help="JSON {origem: 'o que observar'}")
    a = ap.parse_args()

    inv = a.raiz / "inventario.csv"
    if not inv.exists():
        raise SystemExit(f"erro: {inv} não existe. Rode preparar_assets.py --inventario primeiro.")

    with open(inv, encoding="utf-8") as f:
        itens = list(csv.DictReader(f))

    notas = {}
    if a.notas and a.notas.exists():
        notas = json.loads(a.notas.read_text(encoding="utf-8"))

    itens = colapsar_variantes(itens)

    grupos = {}
    for it in itens:
        grupos.setdefault(it.get("origem") or "indefinida", []).append(it)

    partes = [
        "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        f"<title>Moodboard — @{html.escape(a.handle)}</title>",
        f"<style>{CSS}</style></head><body><div class=\"wrap\">",
        "<header><div class=\"eyebrow\">Referência visual · Instagram</div>",
        f"<h1>{html.escape(a.titulo)}</h1>",
        f"<div class=\"meta\">@{html.escape(a.handle)} · montado em "
        f"{date.today().strftime('%d/%m/%Y')} · {len(itens)} itens</div></header>",
    ]

    for origem in ORDEM:
        grupo = grupos.get(origem)
        if not grupo:
            continue
        uso = grupo[0].get("uso", "")
        partes.append(f"<h2>{ROTULO.get(origem, origem)} — {len(grupo)} itens</h2>")
        partes.append(
            f"<div class=\"aviso {CLASSE_USO.get(origem, 'warn')}\">{html.escape(uso)}</div>")
        if notas.get(origem):
            partes.append(f"<div class=\"nota\">{html.escape(notas[origem])}</div>")
        partes.append("<div class=\"grid\">")
        for it in grupo:
            uri = miniatura(a.raiz / it["thumb"]) if it.get("thumb") else ""
            nome = html.escape(it.get("nome") or Path(it["arquivo"]).name)
            dim = it.get("detalhe") or it.get("tipo", "")
            selo = ("<span class=\"selo\">vídeo</span>"
                    if it.get("tipo") == "video" else "")
            corpo = (f"<div class=\"thumb\">{selo}"
                     f"<img src=\"{uri}\" alt=\"{nome}\" loading=\"lazy\"></div>" if uri
                     else f"<div class=\"semimg\">{html.escape(it.get('tipo','arquivo'))}<br>"
                          f"(sem miniatura)</div>")
            partes.append(
                f"<div class=\"item\">{corpo}<div class=\"cap\"><span class=\"n\">{nome}</span>"
                f"<span>{html.escape(str(dim))} · {it.get('peso_kb','?')} KB</span></div></div>")
        partes.append("</div>")

    if not itens:
        partes.append("<p class=\"vazio\">Nenhum item no inventário.</p>")

    partes.append(
        "<footer>Miniaturas embutidas na própria página — ela abre sozinha, sem os "
        "arquivos ao lado. Os originais estão no pacote .zip correspondente. "
        "Material marcado como referência interna não pode ser publicado nem usado "
        "no site do cliente.</footer></div></body></html>")

    a.saida.write_text("".join(partes), encoding="utf-8")
    print(f"moodboard: {a.saida} ({a.saida.stat().st_size // 1024} KB, {len(itens)} itens)")


if __name__ == "__main__":
    main()
