#!/usr/bin/env python3
"""Cria a árvore do dossiê e, no fim, indexa o acervo num HTML navegável.

Uso:
    # no início, com o caminho já aprovado pelo usuário
    python montar_dossie.py --handle turisthermas \\
        --base "C:/Users/Fulano/Downloads/Dossies" --saida projeto/

    # no fim, com o acervo já preenchido
    python montar_dossie.py --indexar "<pasta do dossie>" --saida entregas/indice.html

Um dossiê é diferente de um relatório: o relatório é a opinião, o dossiê é o
acervo que sustenta a opinião e continua servindo depois que a opinião envelhece.
Por isso a árvore separa **origem** (cliente, concorrente, tendência) antes de
separar tipo — é a origem que define o uso permitido, e uso permitido é a coisa
que alguém vai violar por engano daqui a seis meses.
"""

import argparse
import csv
import html
import json
from datetime import date
from pathlib import Path

# Origem -> (rótulo, uso permitido). A tabela existe para que o índice consiga
# carimbar cada arquivo sem depender de alguém lembrar.
USO = {
    "cliente": ("Cliente", "Livre — material do próprio cliente, pode ir para site e feed"),
    "concorrentes": ("Concorrente", "ESTUDO — não publicar. Vale benchmark e teardown"),
    "tendencias": ("Tendência", "ESTUDO — referência de formato e áudio, não publicar"),
    "anuncios": ("Anúncio de terceiro", "ESTUDO — evidência de mídia paga, não publicar"),
    "sites": ("Site", "Citação curta com fonte; não copiar página"),
}

ARVORE = """{nome}/
├── README.md                  este manifesto
├── dados/                     JSON de coleta — a fonte da verdade
│   ├── coleta-<handle>.json
│   ├── anuncios-<handle>.json
│   ├── sites-<handle>.json
│   └── tendencias-<handle>.json
├── acervo/
│   ├── cliente/               videos/  imagens/  capturas/
│   ├── concorrentes/<handle>/ videos/  capturas/
│   ├── tendencias/            videos/  audios/  capturas/
│   └── anuncios/              capturas das bibliotecas Meta e Google
├── teardown/                  o que você viu ao assistir cada vídeo
└── entregas/                  relatório .md e .html, moodboard, índice, zip
"""

MANIFESTO = """# Dossiê — @{handle}

**Aberto em:** {hoje}
**Segmento:** {segmento}
**Vende:** {oferta}
**Objetivo principal:** {objetivo}
**Frequência de postagem declarada:** {frequencia}
**Site do cliente:** {site}
**Nicho (calibra os benchmarks):** {nicho}

## Estrutura

```
{arvore}
```

## Regras de uso do material

| Origem | Uso permitido |
|---|---|
{tabela_uso}

Material de terceiro neste dossiê é **insumo de estudo**. O que sai daqui e vai
para o cliente é o teardown e a leitura — não o arquivo.

## Cotas obrigatórias

O dossiê não é considerado completo sem:

- 3 vídeos do cliente
- **3 vídeos de concorrentes**
- **3 vídeos de tendência** (de fora do nicho direto)
- **5 áudios em alta**
- 10 imagens do cliente em resolução original
- caçada de tendências cobrindo YouTube, TikTok, Instagram e X
- teardown escrito para cada vídeo baixado

`verificar_entrega.py --dossie` confere isso no disco. Enquanto o código de
saída for 1, o dossiê está incompleto.

## Rastreabilidade

Todo número do relatório precisa chegar a um arquivo em `dados/`. Todo arquivo
em `acervo/` precisa aparecer no inventário com origem e uso permitido.

---

*Pasta criada pelo agente `dossie-social`.*
"""

MIDIA = {".mp4": "vídeo", ".mov": "vídeo", ".webm": "vídeo",
         ".mp3": "áudio", ".m4a": "áudio", ".wav": "áudio",
         ".jpg": "imagem", ".jpeg": "imagem", ".png": "imagem", ".webp": "imagem"}


def origem_de(rel: Path):
    partes = rel.parts
    if "acervo" in partes:
        i = partes.index("acervo")
        if len(partes) > i + 1:
            return partes[i + 1]
    return "outros"


def humano(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024


def indexar(raiz: Path, saida: Path):
    """Índice HTML do acervo — a porta de entrada do dossiê."""
    itens = []
    acervo = raiz / "acervo"
    for p in sorted(acervo.rglob("*")) if acervo.is_dir() else []:
        if not p.is_file():
            continue
        rel = p.relative_to(raiz)
        tipo = MIDIA.get(p.suffix.lower())
        if not tipo:
            continue
        itens.append({"arquivo": p.name, "caminho": str(rel).replace("\\", "/"),
                      "origem": origem_de(rel), "tipo": tipo,
                      "bytes": p.stat().st_size})

    por_origem = {}
    for it in itens:
        por_origem.setdefault(it["origem"], []).append(it)

    # inventário em CSV ao lado do índice — é o que sobrevive ao HTML
    inv = saida.parent / "inventario-dossie.csv"
    with inv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arquivo", "caminho", "origem", "tipo", "bytes", "uso_permitido"])
        for it in itens:
            w.writerow([it["arquivo"], it["caminho"], it["origem"], it["tipo"],
                        it["bytes"], USO.get(it["origem"], ("", "verificar"))[1]])

    linhas = []
    for og, lista in sorted(por_origem.items()):
        rot, uso = USO.get(og, (og.title(), "verificar antes de usar"))
        cont = {}
        for it in lista:
            cont[it["tipo"]] = cont.get(it["tipo"], 0) + 1
        resumo = " · ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in sorted(cont.items()))
        peso = humano(sum(i["bytes"] for i in lista))
        linhas.append(f'<section><h2>{html.escape(rot)}</h2>'
                      f'<p class="uso">{html.escape(uso)}</p>'
                      f'<p class="resumo">{resumo} · {peso}</p><ul>')
        for it in sorted(lista, key=lambda x: (x["tipo"], x["arquivo"])):
            linhas.append(f'<li><span class="t">{it["tipo"]}</span> '
                          f'<a href="{html.escape(it["caminho"])}">{html.escape(it["arquivo"])}</a> '
                          f'<span class="b">{humano(it["bytes"])}</span></li>')
        linhas.append("</ul></section>")

    total = humano(sum(i["bytes"] for i in itens)) if itens else "0 B"
    doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Índice do dossiê — {html.escape(raiz.name)}</title><style>
:root{{--bg:#fbfaf9;--surface:#fff;--border:#e6e2dd;--text:#1c1a17;--muted:#6b6560;--accent:#0e7490}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#141312;--surface:#1c1b19;--border:#2f2c29;--text:#f0ede9;--muted:#9c948c;--accent:#67e8f9}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);
font:16px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
.wrap{{max-width:880px;margin:0 auto;padding:48px 24px 80px}}
h1{{font-size:30px;margin:0 0 4px;letter-spacing:-.02em}}
.meta{{color:var(--muted);font-size:14px;margin-bottom:36px}}
section{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px 22px;margin:16px 0}}
h2{{font-size:15px;margin:0 0 4px;letter-spacing:.02em}}
.uso{{font-size:13px;color:var(--muted);margin:0 0 2px}}
.resumo{{font-size:13px;color:var(--accent);margin:0 0 14px}}
ul{{list-style:none;margin:0;padding:0}}
li{{display:flex;gap:10px;align-items:baseline;padding:5px 0;border-top:1px dashed var(--border);font-size:14px}}
li:first-child{{border-top:0}}
.t{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);min-width:56px}}
.b{{margin-left:auto;color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}}
a{{color:var(--accent);text-decoration:none}} a:hover{{text-decoration:underline}}
</style></head><body><div class="wrap">
<h1>Dossiê — {html.escape(raiz.name)}</h1>
<div class="meta">{len(itens)} arquivos · {total} · indexado em {date.today().strftime('%d/%m/%Y')}<br>
Material de terceiro aqui é estudo. O que sai do dossiê é o teardown, não o arquivo.</div>
{''.join(linhas) or '<section><p>Acervo vazio — nada foi baixado ainda.</p></section>'}
</div></body></html>"""
    saida.write_text(doc, encoding="utf-8")
    return len(itens), total, inv


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--handle")
    ap.add_argument("--base", help="pasta escolhida pelo usuário")
    ap.add_argument("--segmento", default="(a definir)")
    ap.add_argument("--oferta", default="(a definir)")
    ap.add_argument("--objetivo", default="(a definir)")
    ap.add_argument("--frequencia", default="(a definir)")
    ap.add_argument("--site", default="(a definir)")
    ap.add_argument("--nicho", default="(a detectar)")
    ap.add_argument("--indexar", type=Path, help="pasta do dossiê a indexar")
    ap.add_argument("--saida", type=Path, default=Path("projeto"))
    a = ap.parse_args()

    if a.indexar:
        saida = a.saida if a.saida.suffix == ".html" else a.saida / "indice.html"
        saida.parent.mkdir(parents=True, exist_ok=True)
        n, peso, inv = indexar(a.indexar, saida)
        print(f"índice: {saida} ({n} arquivos, {peso})")
        print(f"inventário: {inv}")
        if n == 0:
            print("\nAcervo vazio. Um dossiê sem arquivo não é dossiê — "
                  "confira no disco se o download realmente aconteceu.")
        return

    if not a.handle or not a.base:
        ap.error("--handle e --base são obrigatórios para abrir o dossiê")

    handle = a.handle.lstrip("@")
    hoje = date.today()
    nome = f"dossie - {handle} - {hoje.strftime('%d-%m-%Y')}"
    base = a.base.rstrip("/\\")
    windows = ":" in base[:3] or "\\" in base
    if windows:
        base = base.replace("/", "\\")
    sep = "\\" if windows else "/"

    tabela = "\n".join(f"| {rot} | {uso} |" for rot, uso in USO.values())
    a.saida.mkdir(parents=True, exist_ok=True)
    readme = a.saida / "README.md"
    readme.write_text(MANIFESTO.format(
        handle=handle, hoje=hoje.strftime("%d/%m/%Y"), segmento=a.segmento,
        oferta=a.oferta, objetivo=a.objetivo, frequencia=a.frequencia,
        site=a.site, nicho=a.nicho, arvore=ARVORE.format(nome=nome),
        tabela_uso=tabela), encoding="utf-8")

    pasta = f"{base}{sep}{nome}"
    print(f"manifesto: {readme}")
    print(f"pasta do dossiê: {pasta}")
    print("\nGrave o README com device_commit_files em:")
    print(f"  {pasta}{sep}README.md")
    print("\nÉ essa gravação que cria a árvore — não há mkdir pela ponte. "
          "As subpastas nascem quando o primeiro arquivo cai em cada uma.")
    print(f"\nANTES, confira com device_list_dir se '{nome}' já existe. "
          "Se existir, some um sufixo em vez de sobrescrever.")


if __name__ == "__main__":
    main()
