#!/usr/bin/env python3
"""Prepara um vídeo para o Claude assistir: cortes, frames-chave e folha de contatos.

Uso:
    python analisar_video.py video.mp4 --saida pasta/ [--max-frames 12] [--limiar 0.30]

O Claude não recebe um stream de vídeo — ele lê imagens. Este script transforma o
vídeo em algo que ele consegue de fato *olhar*: detecta os cortes, extrai um frame
de cada plano, marca o timestamp em cada um e monta uma folha de contatos.

Com isso na mão, o Claude vê o ritmo de edição, o texto na tela, a progressão do
assunto e onde entra o CTA — que é o que interessa num estudo de referência.

Saída em `<pasta>/`:
    frames/t0.0s.jpg, t1.8s.jpg, ...   um por plano detectado
    contact-sheet.jpg                  todos os frames com timestamp
    analise.json                       metadados + lista de cortes + ritmo
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None


def exige(bin_):
    if shutil.which(bin_) is None:
        sys.exit(f"erro: {bin_} não encontrado. Instale ffmpeg.")


def sonda(v: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(v)],
        capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    vs = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    aud = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    if not vs:
        sys.exit("erro: sem faixa de vídeo.")
    num, den = (vs.get("r_frame_rate") or "0/1").split("/")
    fps = round(float(num) / float(den), 2) if float(den) else None
    dur = float(d["format"].get("duration") or vs.get("duration") or 0)
    w, h = int(vs["width"]), int(vs["height"])
    return {
        "duracao_s": round(dur, 2),
        "resolucao": f"{w}x{h}",
        "proporcao": ("9:16 (vertical)" if h > w * 1.5 else
                      "4:5 (retrato)" if h > w else
                      "1:1 (quadrado)" if h == w else "horizontal"),
        "fps": fps,
        "tem_audio": bool(aud),
        "codec_audio": (aud or {}).get("codec_name"),
        "peso_mb": round(int(d["format"].get("size", 0)) / 1_048_576, 1),
    }


def detectar_cortes(v: Path, limiar: float, min_plano: float = 0.5) -> list:
    """Instantes em que a imagem muda o bastante para ser um corte.

    O detector do ffmpeg sozinho não serve: com limiar alto ele perde os cortes
    de uma montagem de viagem (cenas seguidas de céu, piscina e areia têm
    histograma parecido), e com limiar baixo ele dispara em rajada durante
    movimento de câmera — devolvendo "planos" de 0,03s que não existem.

    A correção é temporal, não de sensibilidade: use limiar baixo para não
    perder corte, e depois colapse tudo que estiver a menos de `min_plano` de
    distância. Duas detecções separadas por 0,1s não são dois planos; são um
    chacoalhão de câmera dentro do mesmo plano.
    """
    r = subprocess.run(
        ["ffmpeg", "-i", str(v), "-filter:v",
         f"select='gt(scene,{limiar})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True)
    brutos = sorted({round(float(m), 2) for m in
                     re.findall(r"pts_time:([0-9.]+)", r.stderr)})
    limpos = []
    for t in brutos:
        if not limpos or t - limpos[-1] >= min_plano:
            limpos.append(t)
    return limpos


def extrair(v: Path, momentos: list, destino: Path, dur: float = 0) -> list:
    """Extrai um frame por momento, deslocado 0,25s para dentro do plano.

    O instante do corte é a fronteira entre dois planos: pedir o frame exato
    devolve o último quadro do plano que acabou, não o primeiro do que começou.
    Um quarto de segundo à frente cai dentro do plano novo — que é o que se
    quer olhar.
    """
    destino.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for t in momentos:
        alvo_t = t + 0.25 if t > 0 else 0.1
        if dur and alvo_t >= dur:
            alvo_t = max(0.0, dur - 0.2)
        alvo = destino / f"t{t:05.1f}s.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(round(alvo_t, 2)),
             "-i", str(v), "-frames:v", "1", "-q:v", "3", str(alvo)],
            check=True)
        if alvo.exists() and alvo.stat().st_size > 0:
            caminhos.append((t, alvo))
    return caminhos


def folha(frames: list, saida: Path, colunas: int = 4, largura: int = 360):
    """Folha de contatos com o timestamp gravado em cada quadro.

    O timestamp é essencial: sem ele dá para ver as cenas mas não o ritmo, e
    ritmo é metade do que se estuda num Reel.
    """
    if Image is None:
        sys.exit("erro: Pillow necessário.")
    if not frames:
        sys.exit("erro: nenhum frame extraído.")
    ims = []
    for t, p in frames:
        im = Image.open(p).convert("RGB")
        im = im.resize((largura, round(im.height * largura / im.width)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        rot = f"{t:.1f}s"
        try:
            fonte = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except Exception:
            fonte = ImageFont.load_default()
        cx = d.textbbox((0, 0), rot, font=fonte)
        d.rectangle([8, 8, 16 + cx[2], 14 + cx[3]], fill=(0, 0, 0))
        d.text((12, 10), rot, fill=(255, 255, 255), font=fonte)
        ims.append(im)

    lh = max(i.height for i in ims)
    linhas = (len(ims) + colunas - 1) // colunas
    pad = 8
    f = Image.new("RGB",
                  (colunas * largura + pad * (colunas + 1),
                   linhas * lh + pad * (linhas + 1)), (16, 16, 16))
    for i, im in enumerate(ims):
        f.paste(im, (pad + (i % colunas) * (largura + pad),
                     pad + (i // colunas) * (lh + pad)))
    f.save(saida, quality=88, optimize=True)
    return f.size


def ritmo(cortes: list, dur: float) -> dict:
    if len(cortes) < 2:
        return {"cortes": len(cortes), "leitura": "plano único ou poucos cortes"}
    inter = [round(cortes[i + 1] - cortes[i], 2) for i in range(len(cortes) - 1)]
    med = round(sum(inter) / len(inter), 2)
    return {
        "cortes": len(cortes),
        "cortes_por_minuto": round(len(cortes) / dur * 60, 1) if dur else None,
        "duracao_media_do_plano_s": med,
        "plano_mais_curto_s": min(inter),
        "plano_mais_longo_s": max(inter),
        "leitura": (
            "corte muito rápido — estilo de retenção agressiva" if med < 1.2 else
            "ritmo rápido, padrão de Reel educativo" if med < 2.5 else
            "ritmo médio, dá tempo de ler texto na tela" if med < 4.5 else
            "ritmo lento, aposta em imagem e atmosfera"
        ),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--max-frames", type=int, default=12)
    ap.add_argument("--limiar", type=float, default=0.15,
                    help="sensibilidade bruta do detector (padrão 0.15, baixo de propósito)")
    ap.add_argument("--min-plano", type=float, default=0.5,
                    help="duração mínima de um plano em segundos; detecções mais "
                         "próximas que isso são fundidas (padrão 0.5)")
    a = ap.parse_args()

    exige("ffmpeg"); exige("ffprobe")
    if not a.video.exists():
        sys.exit(f"erro: {a.video} não existe.")

    meta = sonda(a.video)
    cortes = detectar_cortes(a.video, a.limiar, a.min_plano)

    # Um frame por plano. Sem cortes detectados, distribui uniformemente — um
    # vídeo de plano único ainda tem progressão de texto na tela para ler.
    momentos = [0.0] + cortes
    if len(momentos) > a.max_frames:
        passo = len(momentos) / a.max_frames
        momentos = [momentos[int(i * passo)] for i in range(a.max_frames)]
    elif len(momentos) < 4 and meta["duracao_s"] > 4:
        n = min(a.max_frames, 8)
        momentos = [round(meta["duracao_s"] * i / n, 2) for i in range(n)]

    a.saida.mkdir(parents=True, exist_ok=True)
    frames = extrair(a.video, momentos, a.saida / "frames", meta["duracao_s"])
    tam = folha(frames, a.saida / "contact-sheet.jpg")

    r = {
        "arquivo": a.video.name,
        "metadados": meta,
        "ritmo": ritmo(cortes, meta["duracao_s"]),
        "cortes_detectados_s": cortes[:40],
        "frames": [{"t": t, "arquivo": str(p.relative_to(a.saida))} for t, p in frames],
        "contact_sheet": "contact-sheet.jpg",
        "proximo_passo": (
            "Leia contact-sheet.jpg e os frames individuais com a ferramenta Read, "
            "e escreva o teardown seguindo references/estudo-de-referencia.md"
        ),
    }
    (a.saida / "analise.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== {a.video.name} ===")
    print(f"{meta['resolucao']} · {meta['proporcao']} · {meta['duracao_s']}s · "
          f"{meta['fps']}fps · {meta['peso_mb']} MB · áudio: {meta['tem_audio']}")
    print(f"\nRitmo: {r['ritmo']}")
    print(f"\n{len(frames)} frames -> {a.saida / 'frames'}")
    print(f"Folha de contatos {tam[0]}x{tam[1]} -> {a.saida / 'contact-sheet.jpg'}")
    print(f"JSON -> {a.saida / 'analise.json'}")
    print("\nAgora LEIA a folha de contatos. O script prepara; quem assiste é você.")


if __name__ == "__main__":
    main()
