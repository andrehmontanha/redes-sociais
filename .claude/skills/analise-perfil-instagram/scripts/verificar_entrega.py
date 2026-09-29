#!/usr/bin/env python3
"""Trava de entrega: confere se a análise está completa antes de ser declarada pronta.

Uso:
    python verificar_entrega.py <pasta-da-analise> [--min-comparacao 3] [--json]

Existe porque "lembrar de entregar tudo" não é um mecanismo. Numa execução real
desta skill faltaram o HTML, os assets e quatro dos cinco perfis de comparação —
e nada avisou. Este script avisa.

Ele confere o que precisa existir no disco:

    <analise>/
    ├── README.md                      manifesto com as respostas de abertura
    ├── dados/*.json                    a coleta — fonte da verdade
    ├── assets/                         material capturado
    │   └── **/*.mp4                    vídeos REALMENTE baixados
    ├── teardown/*teardown*.md          o que você viu ao assistir
    ├── dados/anuncios-*.json           Meta + Google: quem compra mídia
    └── entregas/
        ├── *.md                        relatório em Markdown
        └── *.html                      relatório visual  ← o mais esquecido

E, um nível acima, se há perfis de comparação suficientes.

Saída: lista do que falta e código 1 se houver bloqueio. Enquanto o código for 1,
a análise **não está pronta** — nem para o cliente, nem para dizer que terminou.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Itens que impedem a entrega. Os avisos são recomendações; os bloqueios, não.
BLOQUEIOS = "bloqueios"
AVISOS = "avisos"


def achar_raiz_cliente(analise: Path) -> Path:
    """A pasta do @ do cliente é a mãe da pasta 'analise - DD-MM-AAAA'."""
    return analise.parent


def contar_comparacao(raiz: Path):
    """Perfis em 'perfis de comparação/' que tenham ao menos uma análise com dados."""
    pasta = raiz / "perfis de comparação"
    if not pasta.is_dir():
        return [], []
    completos, vazios = [], []
    for p in sorted(pasta.iterdir()):
        if not p.is_dir():
            continue
        # `any(d.glob(...) for ...)` seria sempre verdadeiro: generator vazio é
        # truthy. A trava passaria com pasta vazia — que é exatamente o defeito
        # que ela existe para pegar.
        tem_dados = any(any(d.glob("*.json"))
                        for d in p.glob("analise - */dados") if d.is_dir())
        (completos if tem_dados else vazios).append(p.name)
    return completos, vazios


# Cotas do modo dossiê. Existem porque "material de referência" sem arquivo é
# opinião: a leitura de tendência só é auditável se o vídeo e o áudio estiverem
# no disco seis meses depois.
COTAS_DOSSIE = {
    "cliente/videos": ("vídeos do cliente", 3, (".mp4", ".mov", ".webm")),
    "concorrentes": ("vídeos de concorrentes", 3, (".mp4", ".mov", ".webm")),
    "tendencias/videos": ("vídeos de tendência", 3, (".mp4", ".mov", ".webm")),
    "tendencias/audios": ("áudios em alta", 5, (".m4a", ".mp3", ".wav")),
    "cliente/imagens": ("imagens do cliente", 10, (".jpg", ".jpeg", ".png", ".webp")),
}


def conferir_dossie(analise: Path, r):
    """Conta o acervo por origem. Só o disco vale — retorno de navegador mente."""
    acervo = analise / "acervo"
    achados = {}
    for sub, (rotulo, minimo, exts) in COTAS_DOSSIE.items():
        pasta = acervo / sub
        qtd = 0
        if pasta.is_dir():
            qtd = sum(1 for x in pasta.rglob("*")
                      if x.is_file() and x.suffix.lower() in exts)
        achados[rotulo] = qtd
        if qtd < minimo:
            r[BLOQUEIOS].append(
                f"{rotulo}: {qtd} de {minimo} — cota obrigatória do dossiê. "
                f"Confira no disco: {pasta}")
    r["encontrado"]["dossie"] = achados

    # a caçada de tendências precisa ter passado pelas quatro plataformas
    pasta_dados = analise / "dados"
    tend = sorted(pasta_dados.glob("tendencias-*.json")) if pasta_dados.is_dir() else []
    if not tend:
        r[BLOQUEIOS].append(
            "sem dados/tendencias-<handle>.json — a caçada nas quatro plataformas não rodou")
    else:
        try:
            d = json.loads(tend[0].read_text(encoding="utf-8"))
            plats = {str(x.get("plataforma", "")).lower()
                     for x in (d.get("itens") or d.get("tendencias") or [])}
            faltam = [q for q in ("youtube", "tiktok", "instagram", "x")
                      if not any(q == t or q in t for t in plats)]
            if faltam:
                r[BLOQUEIOS].append(
                    "caçada incompleta — sem itens de: " + ", ".join(faltam)
                    + ". As quatro plataformas são obrigatórias")
        except Exception as e:
            r[BLOQUEIOS].append(f"tendencias-*.json ilegível: {str(e)[:70]}")

    if not (analise / "entregas" / "indice.html").is_file():
        r[AVISOS].append("sem entregas/indice.html — rode montar_dossie.py --indexar")


def verificar(analise: Path, min_comp: int, min_videos: int = 4,
              min_teardowns: int = 2, dossie: bool = False):
    r = {BLOQUEIOS: [], AVISOS: [], "encontrado": {}}

    if not analise.is_dir():
        r[BLOQUEIOS].append(f"a pasta da análise não existe: {analise}")
        return r

    # --- manifesto ---
    readme = analise / "README.md"
    if readme.is_file():
        txt = readme.read_text(encoding="utf-8", errors="ignore")
        r["encontrado"]["README.md"] = True
        for campo, rotulo in (("Segmento", "segmento"), ("Vende", "produtos ou serviços"),
                              ("Objetivo principal", "objetivo"),
                              ("Frequência", "frequência declarada")):
            if campo not in txt:
                r[AVISOS].append(f"README sem o campo '{rotulo}' — era uma das perguntas de abertura")
    else:
        r[BLOQUEIOS].append("falta README.md — o manifesto com as respostas de abertura")

    # --- dados ---
    dados = sorted((analise / "dados").glob("*.json")) if (analise / "dados").is_dir() else []
    r["encontrado"]["dados"] = [d.name for d in dados]
    if not dados:
        r[BLOQUEIOS].append("pasta dados/ vazia — sem coleta não há número rastreável")

    # --- entregas ---
    ent = analise / "entregas"
    mds = sorted(ent.glob("*.md")) if ent.is_dir() else []
    htmls = sorted(ent.glob("*.html")) if ent.is_dir() else []
    r["encontrado"]["entregas_md"] = [m.name for m in mds]
    r["encontrado"]["entregas_html"] = [h.name for h in htmls]

    relatorios = [m for m in mds if not m.name.startswith("historico")]
    if not relatorios:
        r[BLOQUEIOS].append("falta o relatório em Markdown em entregas/")
    if not htmls:
        r[BLOQUEIOS].append("falta o relatório em HTML em entregas/ — "
                            "é o formato que vai para o cliente, e o mais esquecido")

    # --- assets ---
    #
    # No modo dossiê o material vive em `acervo/`, organizado por origem, e as
    # cotas de lá substituem esta checagem — exigir as duas pastas faria a trava
    # bloquear um dossiê completo.
    assets = analise / "assets"
    arquivos_asset = [p for p in assets.rglob("*") if p.is_file()] if assets.is_dir() else []
    r["encontrado"]["assets"] = len(arquivos_asset)
    if not arquivos_asset and not dossie:
        r[BLOQUEIOS].append("pasta assets/ vazia — nenhum conteúdo foi capturado ou baixado")
    elif len(arquivos_asset) < 5 and not dossie:
        r[AVISOS].append(f"apenas {len(arquivos_asset)} arquivo(s) em assets/ — "
                         "confira se a captura rodou de verdade")
    if assets.is_dir() and not dossie and not (assets / "inventario.csv").is_file():
        r[AVISOS].append("assets/ sem inventario.csv — sem ele ninguém sabe a origem "
                         "e o uso permitido de cada arquivo")

    # --- vídeos baixados ---
    #
    # Existe porque "baixei" foi reportado sem que nenhum arquivo chegasse ao
    # disco: o Chrome bloqueia o segundo download em diante e o JavaScript
    # devolve sucesso mesmo assim. Só o disco diz a verdade.
    videos = [p for p in analise.rglob("*")
              if p.is_file() and p.suffix.lower() in (".mp4", ".mov", ".webm")]
    proprios = [v for v in videos if "cliente" in str(v).lower()]
    referencia = [v for v in videos if v not in proprios]
    r["encontrado"]["videos"] = [v.name for v in videos]
    if len(videos) < min_videos:
        r[BLOQUEIOS].append(
            f"apenas {len(videos)} vídeo(s) baixado(s) (mínimo {min_videos}) — "
            "confira no disco, não no retorno do navegador: o Chrome bloqueia o "
            "segundo download em diante e ainda assim reporta sucesso")
    elif not proprios or not referencia:
        r[AVISOS].append(
            "os vídeos são todos do mesmo lado — sem cliente E referência não há "
            "contraste, e é o contraste que vira diretriz")

    # --- teardowns escritos ---
    tds = [p for p in analise.rglob("*.md") if "teardown" in p.name.lower()]
    marcas = 0
    for t in tds:
        marcas += len(re.findall(r"\d+[,.]\d+\s*s\b",
                                 t.read_text(encoding="utf-8", errors="ignore")))
    r["encontrado"]["teardowns"] = [t.name for t in tds]
    if not tds:
        r[BLOQUEIOS].append(
            "nenhum teardown escrito — baixar vídeo sem assistir não é análise")
    elif marcas < min_teardowns * 6:
        r[BLOQUEIOS].append(
            f"teardown sem leitura de imagem: só {marcas} referência(s) a timestamp "
            "no texto — descrever cadência de corte a partir do JSON não é assistir")

    # --- bibliotecas de anúncios ---
    #
    # O feed diz o que a marca posta; só a biblioteca diz o que ela compra.
    # Numa execução real, o cliente tinha 22 anúncios no Google, zero na Meta, e
    # o termo central do negócio dele tinha 280 anúncios ativos de terceiros.
    anun = sorted((analise / "dados").glob("anuncios-*.json")) if (analise / "dados").is_dir() else []
    r["encontrado"]["anuncios"] = [a.name for a in anun]
    if not anun:
        r[BLOQUEIOS].append(
            "sem levantamento das bibliotecas de anúncios — falta "
            "dados/anuncios-<handle>.json (Meta e Google)")
    else:
        try:
            d = json.loads(anun[0].read_text(encoding="utf-8"))
            marcas = {x.get("handle") or x.get("anunciante")
                      for x in ((d.get("meta") or {}).get("por_anunciante") or [])}
            marcas |= {x.get("handle") or x.get("anunciante")
                       for x in ((d.get("google") or {}).get("por_anunciante") or [])}
            marcas.discard(None)
            termos = (d.get("meta") or {}).get("por_termo") or []
            if len(marcas) < 4:
                r[BLOQUEIOS].append(
                    f"anúncios de apenas {len(marcas)} marca(s) — o mínimo é o cliente "
                    "e três concorrentes, senão não há comparação")
            if not termos:
                r[AVISOS].append(
                    "nenhum termo de mercado levantado — a disputa por termo é o que "
                    "mostra quem está comprando a audiência do cliente")
        except Exception as e:
            r[BLOQUEIOS].append(f"anuncios-*.json ilegível: {str(e)[:70]}")

    if dossie:
        conferir_dossie(analise, r)

    # --- perfis de comparação ---
    raiz = achar_raiz_cliente(analise)
    completos, vazios = contar_comparacao(raiz)
    r["encontrado"]["perfis_comparacao"] = completos
    if len(completos) < min_comp:
        r[BLOQUEIOS].append(
            f"apenas {len(completos)} perfil(is) de comparação com dados "
            f"(mínimo {min_comp}) — um perfil só não é benchmark, é anedota")
    if vazios:
        r[AVISOS].append(f"pastas de comparação sem dados: {', '.join(vazios)}")

    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("analise", type=Path)
    ap.add_argument("--min-comparacao", type=int, default=3)
    ap.add_argument("--min-videos", type=int, default=4,
                    help="mínimo de vídeos .mp4 baixados de verdade")
    ap.add_argument("--min-teardowns", type=int, default=2,
                    help="mínimo de vídeos com teardown escrito")
    ap.add_argument("--dossie", action="store_true",
                    help="modo dossiê: exige as cotas de acervo e a caçada nas 4 plataformas")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    r = verificar(a.analise, a.min_comparacao, a.min_videos, a.min_teardowns,
                  a.dossie)

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== Verificação de entrega — {a.analise.name} ===\n")
        enc = r["encontrado"]
        print(f"dados/          {len(enc.get('dados') or [])} arquivo(s)")
        print(f"assets/         {enc.get('assets', 0)} arquivo(s)")
        print(f"vídeos          {len(enc.get('videos') or [])} baixado(s)")
        print(f"teardowns       {len(enc.get('teardowns') or [])}")
        print(f"anúncios        {len(enc.get('anuncios') or [])} arquivo(s)")
        if enc.get("dossie"):
            for rot, qtd in enc["dossie"].items():
                print(f"  acervo · {rot:26}{qtd}")
        print(f"entregas/ .md   {len(enc.get('entregas_md') or [])}")
        print(f"entregas/ .html {len(enc.get('entregas_html') or [])}")
        print(f"comparação      {len(enc.get('perfis_comparacao') or [])} perfil(is): "
              f"{', '.join(enc.get('perfis_comparacao') or ['—'])}")

        if r[BLOQUEIOS]:
            print(f"\n❌ BLOQUEIOS ({len(r[BLOQUEIOS])}) — a análise NÃO está pronta:")
            for b in r[BLOQUEIOS]:
                print(f"   • {b}")
        if r[AVISOS]:
            print(f"\n⚠  Avisos ({len(r[AVISOS])}):")
            for w in r[AVISOS]:
                print(f"   • {w}")
        if not r[BLOQUEIOS]:
            print("\n✅ Entrega completa.")
        print()

    sys.exit(1 if r[BLOQUEIOS] else 0)


if __name__ == "__main__":
    main()
