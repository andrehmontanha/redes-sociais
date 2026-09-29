#!/usr/bin/env python3
"""Baixa, otimiza, monta contact sheets e empacota os assets da análise.

Modos (um por execução):

    --baixar urls.json --destino DIR      baixa mídia do cliente a partir de URLs do DOM
    --otimizar DIR --destino DIR          gera webp/jpg em 3 larguras + vídeo comprimido
    --contact-sheet DIR --saida X.jpg     junta frames de um Reel numa folha de contatos
    --empacotar DIR --saida X.zip         monta o pacote final
    --inventario DIR                      (re)gera o inventario.csv de uma pasta

O inventário carrega origem, dono e uso permitido de cada arquivo. Seis meses
depois ninguém lembra de onde veio a foto — e é aí que alguém publica material
de concorrente por engano.
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

LARGURAS = [400, 800, 1600]
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
VID_EXT = {".mp4", ".mov", ".webm", ".m4v"}

# Uso permitido por pasta de origem. A fronteira é a mesma do reference:
# cliente vai para o site; o resto é referência interna.
USO_POR_ORIGEM = {
    "cliente": "livre — material do cliente",
    "criadores": "só com autorização escrita do criador",
    "concorrentes": "REFERÊNCIA INTERNA — não publicar",
    "estudo": "ESTUDO — insumo temporário, não publicar nem reutilizar",
    "bancos": "conforme licença do banco",
}


def origem_de(caminho: Path) -> str:
    partes = {p.lower() for p in caminho.parts}
    for chave in USO_POR_ORIGEM:
        if chave in partes:
            return chave
    return "indefinida"


def uso_de(origem: str) -> str:
    return USO_POR_ORIGEM.get(origem, "VERIFICAR ANTES DE USAR")


def tem_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def slug(texto: str, limite: int = 48) -> str:
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return (t or "asset")[:limite]


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #

def baixar(arquivo_urls: Path, destino: Path):
    """Baixa a mídia listada num JSON extraído do DOM.

    Formato esperado:
      [{"url": "...", "tema": "cafe da manha", "post": "https://...", "tipo": "video"}]

    URLs de mídia do Instagram são assinadas e expiram em algumas horas: se um
    download falhar com 403, quase sempre é validade, não bloqueio — recolete a
    URL. Se falhar de verdade, o script registra e segue; não tente rotas
    alternativas.
    """
    import requests

    destino.mkdir(parents=True, exist_ok=True)
    itens = json.loads(arquivo_urls.read_text(encoding="utf-8"))
    ok, falhas = 0, []

    for i, item in enumerate(itens, 1):
        url = item.get("url")
        if not url:
            continue
        tipo = item.get("tipo") or ("video" if ".mp4" in url.split("?")[0] else "imagem")
        ext = ".mp4" if tipo == "video" else ".jpg"
        nome = f"{i:02d}-{slug(item.get('tema', ''))}{ext}"
        alvo = destino / nome
        try:
            r = requests.get(url, timeout=45, stream=True,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            with open(alvo, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
            # Guarda a procedência junto do arquivo.
            (destino / (nome + ".origem.json")).write_text(
                json.dumps({"post": item.get("post"), "tema": item.get("tema")},
                           ensure_ascii=False), encoding="utf-8")
            print(f"  ok   {nome}  ({alvo.stat().st_size // 1024} KB)")
            ok += 1
        except Exception as e:
            print(f"  FALHA {nome}: {e}", file=sys.stderr)
            falhas.append({"url": url[:80], "erro": str(e)[:120]})

    print(f"\n{ok} baixados, {len(falhas)} falhas.")
    if falhas:
        print("Falhas ficam no relatório como limitação. Se foram 403, recolete as "
              "URLs (elas expiram) — não tente contornar bloqueio.")


# --------------------------------------------------------------------------- #
# Otimização
# --------------------------------------------------------------------------- #

def otimizar_imagem(src: Path, destino: Path, linhas: list):
    if Image is None:
        print("  Pillow ausente — pulei imagens. pip install Pillow", file=sys.stderr)
        return
    with Image.open(src) as im:
        im = im.convert("RGB")
        w0, h0 = im.size
        base = slug(src.stem)
        for largura in LARGURAS:
            if largura > w0 * 1.1:
                continue  # não faz upscale: só aumenta o peso, não a qualidade
            h = round(h0 * largura / w0)
            red = im.resize((largura, h), Image.LANCZOS)
            for ext, kwargs in ((".webp", {"quality": 82, "method": 5}),
                                (".jpg", {"quality": 84, "optimize": True, "progressive": True})):
                alvo = destino / f"{base}-{largura}{ext}"
                red.save(alvo, **kwargs)
                linhas.append({
                    "arquivo": str(alvo.relative_to(destino.parent.parent))
                    if destino.parent.parent in alvo.parents else alvo.name,
                    "tipo": "imagem", "largura": largura, "altura": h,
                    "peso_kb": alvo.stat().st_size // 1024,
                    "origem": origem_de(src), "uso": uso_de(origem_de(src)),
                    "post": "", "alt": f"{src.stem.replace('-', ' ')} — revisar",
                })
        print(f"  imagem {src.name}: {w0}x{h0} -> {len(LARGURAS)} larguras (webp+jpg)")


def otimizar_video(src: Path, destino: Path, linhas: list):
    if not tem_ffmpeg():
        print("  ffmpeg ausente — pulei vídeos.", file=sys.stderr)
        return
    base = slug(src.stem)
    saida = destino / f"{base}.mp4"
    poster = destino / f"{base}-poster.jpg"

    # CRF 26 + faststart: peso aceitável para hero e começa a tocar antes de
    # baixar inteiro. Sem áudio: hero de site toca mudo, e o áudio do Reel
    # costuma ser faixa de terceiro que não pode ir para o site.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-vcodec", "libx264", "-crf", "26", "-preset", "medium",
         "-movflags", "+faststart", "-an", str(saida)],
        check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-vf", "select=eq(n\\,0)", "-q:v", "3", "-frames:v", "1", str(poster)],
        check=True)

    for alvo, tipo in ((saida, "video"), (poster, "poster")):
        linhas.append({
            "arquivo": alvo.name, "tipo": tipo, "largura": "", "altura": "",
            "peso_kb": alvo.stat().st_size // 1024,
            "origem": origem_de(src), "uso": uso_de(origem_de(src)),
            "post": "", "alt": "",
        })
    print(f"  vídeo  {src.name}: {saida.stat().st_size // 1024} KB + poster")


def otimizar(origem: Path, destino: Path):
    destino.mkdir(parents=True, exist_ok=True)
    linhas = []
    arquivos = [p for p in sorted(origem.rglob("*")) if p.is_file()]
    if not arquivos:
        sys.exit(f"erro: nenhum arquivo em {origem}")

    for p in arquivos:
        ext = p.suffix.lower()
        if ext in IMG_EXT:
            otimizar_imagem(p, destino, linhas)
        elif ext in VID_EXT:
            otimizar_video(p, destino, linhas)

    # O inventário é gerado uma vez só, na raiz de assets/, por --inventario ou
    # por --empacotar. Escrever um aqui criaria um segundo arquivo de controle
    # numa subpasta — e duas listas de proveniência divergentes são piores que
    # nenhuma.
    print(f"\n{len(linhas)} variantes geradas em {destino}")
    print("Rode --inventario na raiz de assets/ para consolidar a procedência.")


# --------------------------------------------------------------------------- #
# Contact sheet
# --------------------------------------------------------------------------- #

def contact_sheet(pasta: Path, saida: Path, colunas: int = 3):
    """Junta frames capturados de um Reel numa folha de contatos.

    É a peça mais útil do moodboard: com 6 a 9 frames lado a lado dá para ver o
    ritmo de corte, onde entra o texto na tela e como o assunto evolui — coisas
    invisíveis em métrica e em screenshot solto.
    """
    if Image is None:
        sys.exit("erro: Pillow necessário para contact sheet.")
    frames = [p for p in sorted(pasta.iterdir())
              if p.is_file() and p.suffix.lower() in IMG_EXT]
    if not frames:
        sys.exit(f"erro: nenhum frame em {pasta}")

    imgs = [Image.open(p).convert("RGB") for p in frames]
    lw = 420
    esc = [im.resize((lw, round(im.height * lw / im.width)), Image.LANCZOS) for im in imgs]
    lh = max(im.height for im in esc)
    linhas = (len(esc) + colunas - 1) // colunas
    pad = 8
    folha = Image.new("RGB",
                      (colunas * lw + pad * (colunas + 1),
                       linhas * lh + pad * (linhas + 1)),
                      (18, 18, 18))
    for i, im in enumerate(esc):
        x = pad + (i % colunas) * (lw + pad)
        y = pad + (i // colunas) * (lh + pad)
        folha.paste(im, (x, y))
    saida.parent.mkdir(parents=True, exist_ok=True)
    folha.save(saida, quality=86, optimize=True)
    print(f"contact sheet com {len(esc)} frames -> {saida} "
          f"({saida.stat().st_size // 1024} KB)")


# --------------------------------------------------------------------------- #
# Inventário e empacotamento
# --------------------------------------------------------------------------- #

CAMPOS = ["arquivo", "tipo", "largura", "altura", "peso_kb", "origem", "uso", "post", "alt"]


def escrever_inventario(raiz: Path, linhas: list, anexar: bool = False):
    alvo = raiz / "inventario.csv"
    existentes = []
    if anexar and alvo.exists():
        with open(alvo, encoding="utf-8") as f:
            existentes = list(csv.DictReader(f))
    with open(alvo, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for l in existentes + linhas:
            w.writerow({k: l.get(k, "") for k in CAMPOS})
    print(f"inventário: {alvo} ({len(existentes) + len(linhas)} itens)")


def inventariar(raiz: Path):
    linhas = []
    for p in sorted(raiz.rglob("*")):
        if not p.is_file() or p.suffix.lower() in {".csv", ".html", ".json"}:
            continue
        org = origem_de(p)
        item = {"arquivo": str(p.relative_to(raiz)), "peso_kb": p.stat().st_size // 1024,
                "origem": org, "uso": uso_de(org), "post": "", "alt": ""}
        if p.suffix.lower() in IMG_EXT and Image is not None:
            try:
                with Image.open(p) as im:
                    item["largura"], item["altura"] = im.size
            except Exception:
                pass
            item["tipo"] = "imagem"
            if org == "cliente":
                # Sugestão a partir do nome do arquivo — ponto de partida para
                # quem for publicar, não texto final. Alt errado é pior que
                # alt ausente, então marque que precisa de revisão.
                base = p.stem.rsplit("-", 1)[0] if p.stem[-4:].strip("-").isdigit() else p.stem
                item["alt"] = f"{base.replace('-', ' ')} — revisar"
        elif p.suffix.lower() in VID_EXT:
            item["tipo"] = "video"
        else:
            item["tipo"] = "outro"
        linhas.append(item)
    escrever_inventario(raiz, linhas)
    return linhas


def empacotar(raiz: Path, saida: Path):
    if not (raiz / "inventario.csv").exists():
        inventariar(raiz)
    n = 0
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(raiz.rglob("*")):
            if p.is_file() and not p.name.endswith(".origem.json"):
                z.write(p, Path(saida.stem) / p.relative_to(raiz))
                n += 1
    print(f"pacote: {saida} ({n} arquivos, {saida.stat().st_size // 1024} KB)")


# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baixar", type=Path, help="JSON com as URLs de mídia do cliente")
    ap.add_argument("--otimizar", type=Path, help="pasta de originais")
    ap.add_argument("--contact-sheet", type=Path, help="pasta com os frames de um Reel")
    ap.add_argument("--empacotar", type=Path, help="raiz de assets/ a empacotar")
    ap.add_argument("--inventario", type=Path, help="raiz de assets/ a inventariar")
    ap.add_argument("--destino", type=Path)
    ap.add_argument("--saida", type=Path)
    ap.add_argument("--colunas", type=int, default=3)
    a = ap.parse_args()

    if a.baixar:
        if not a.destino:
            ap.error("--baixar exige --destino")
        baixar(a.baixar, a.destino)
    elif a.otimizar:
        if not a.destino:
            ap.error("--otimizar exige --destino")
        otimizar(a.otimizar, a.destino)
    elif a.contact_sheet:
        if not a.saida:
            ap.error("--contact-sheet exige --saida")
        contact_sheet(a.contact_sheet, a.saida, a.colunas)
    elif a.empacotar:
        if not a.saida:
            ap.error("--empacotar exige --saida")
        empacotar(a.empacotar, a.saida)
    elif a.inventario:
        inventariar(a.inventario)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
