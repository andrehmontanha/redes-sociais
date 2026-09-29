#!/usr/bin/env python3
"""Separa o áudio dos vídeos baixados e mede o que dá para medir sem ouvir.

Uso:
    python extrair_audio.py acervo/tendencias/videos/ --saida acervo/tendencias/audios/
    python extrair_audio.py um-video.mp4 --saida audios/ --formato wav

Para cada vídeo devolve:
  - a faixa em .m4a (cópia do stream, sem recodificar) ou .wav se pedido
  - duração, canais, taxa de amostragem, bitrate
  - **loudness integrado (LUFS) e faixa dinâmica**, via o filtro loudnorm do ffmpeg
  - **envelope de energia por segundo**, e a partir dele os picos — os instantes
    em que a faixa "vira"
  - uma forma de onda em PNG com os picos marcados

Por que isso importa: o teardown de vídeo mede ritmo de corte, e o ritmo de corte
sozinho não explica retenção. **O que explica é o corte cair no pico do áudio.**
Com o envelope ao lado dos cortes dá para dizer "os cortes ignoram a batida" —
que é uma diretriz de produção, não uma observação.

O que este script NÃO faz, de propósito: não transcreve, não identifica a música
e não adivinha o nome da faixa. Se a letra ou a fala importar, diga que não foi
analisada — nunca invente.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

VIDEO = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def ffprobe(v):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(v)],
        capture_output=True, text=True)
    if r.returncode:
        return None
    d = json.loads(r.stdout)
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not a:
        return None
    return {
        "duracao_s": round(float(d["format"].get("duration", 0)), 2),
        "codec": a.get("codec_name"),
        "canais": a.get("channels"),
        "amostragem_hz": int(a.get("sample_rate", 0) or 0),
        "bitrate_kbps": round(int(a.get("bit_rate", 0) or 0) / 1000) or None,
    }


def loudness(v):
    """LUFS integrado e faixa dinâmica. É o que separa áudio 'de trend'
    (esmagado, alto o tempo todo) de áudio de locução."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(v),
         "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
        return {"lufs": float(d["input_i"]), "faixa_dinamica_lu": float(d["input_lra"]),
                "pico_real_dbfs": float(d["input_tp"])}
    except Exception:
        return {}


def envelope(v, passo=1.0):
    """Energia RMS por segundo.

    A armadilha aqui: `astats reset=N` conta N *quadros de áudio*, não segundos —
    usá-lo direto devolve centenas de valores por minuto e transforma qualquer
    variação em "pico". A correção é reamostrar para 8 kHz e fatiar em janelas de
    8000 amostras, o que faz cada janela valer exatamente um segundo.
    """
    n = max(1, int(8000 * passo))
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(v),
         "-af", f"aresample=8000,asetnsamples=n={n}:p=0,"
                "astats=metadata=1:reset=1,"
                "ametadata=print:key=lavfi.astats.Overall.RMS_level",
         "-f", "null", "-"],
        capture_output=True, text=True)
    return [float(x) for x in re.findall(r"RMS_level=(-?[\d.]+)", r.stderr)]


def picos(env, margem=3.0):
    """Instantes em que a energia salta acima da mediana + margem (dB).

    Segundos vizinhos acima do limiar são o *mesmo* pico — um refrão de cinco
    segundos não são cinco eventos. Colapsa a sequência no instante em que ela
    começa, que é o que interessa para casar com um corte.
    """
    if len(env) < 4:
        return []
    ordenado = sorted(env)
    mediana = ordenado[len(ordenado) // 2]
    acima = [i for i, v in enumerate(env) if v >= mediana + margem]
    inicios, anterior = [], None
    for i in acima:
        if anterior is None or i - anterior > 1:
            inicios.append(i)
        anterior = i
    return inicios


def onda(v, destino, env, marcas):
    """PNG da forma de onda com os picos marcados. Serve para ler junto com a
    folha de contatos do vídeo."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(v),
         "-filter_complex", "showwavespic=s=1200x260:colors=#0e7490",
         "-frames:v", "1", str(destino)], capture_output=True, text=True)
    if r.returncode or not destino.exists():
        return None
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return destino
    im = Image.open(destino).convert("RGB")
    w, h = im.size
    d = ImageDraw.Draw(im)
    n = max(1, len(env))
    for i in marcas:
        x = int(i / n * w)
        d.line([(x, 0), (x, h)], fill=(185, 28, 28), width=2)
        d.text((min(x + 4, w - 30), 4), f"{i}s", fill=(185, 28, 28))
    im.save(destino, quality=88)
    return destino


def extrair(v: Path, saida: Path, formato: str):
    saida.mkdir(parents=True, exist_ok=True)
    base = saida / v.stem
    meta = ffprobe(v)
    if not meta:
        return {"arquivo": v.name, "erro": "sem faixa de áudio"}

    if formato == "wav":
        alvo = base.with_suffix(".wav")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(v),
               "-vn", "-acodec", "pcm_s16le", "-ar", "44100", str(alvo)]
    else:
        alvo = base.with_suffix(".m4a")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(v),
               "-vn", "-acodec", "copy", str(alvo)]
        if meta.get("codec") not in ("aac", "alac"):
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(v),
                   "-vn", "-acodec", "aac", "-b:a", "160k", str(alvo)]
    if subprocess.run(cmd, capture_output=True).returncode:
        return {"arquivo": v.name, "erro": "ffmpeg falhou ao extrair"}

    env = envelope(v)
    marcas = picos(env)
    png = onda(v, base.with_name(base.name + "-onda.png"), env, marcas)

    return {
        "arquivo": v.name,
        "audio": alvo.name,
        "onda": png.name if png else None,
        **meta,
        **loudness(v),
        "energia_por_segundo_db": [round(x, 1) for x in env],
        "picos_s": marcas,
        "nota": ("Compare 'picos_s' com os cortes do teardown: corte que cai no "
                 "pico segura atenção; corte fora dele parece aleatório."),
        "nao_analisado": "letra, fala e identificação da faixa — nada aqui é transcrição",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", type=Path, help="vídeo ou pasta de vídeos")
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--formato", choices=["m4a", "wav"], default="m4a")
    a = ap.parse_args()

    if a.entrada.is_dir():
        videos = sorted(p for p in a.entrada.rglob("*") if p.suffix.lower() in VIDEO)
    elif a.entrada.is_file():
        videos = [a.entrada]
    else:
        sys.exit(f"erro: não encontrei {a.entrada}")
    if not videos:
        sys.exit("erro: nenhum vídeo na pasta — o download não aconteceu. "
                 "Confira no disco, não no retorno do navegador.")

    res = [extrair(v, a.saida, a.formato) for v in videos]
    (a.saida / "audios.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = [r for r in res if not r.get("erro")]
    print(f"{len(ok)}/{len(res)} faixas extraídas -> {a.saida}")
    for r in res:
        if r.get("erro"):
            print(f"  ! {r['arquivo']}: {r['erro']}")
        else:
            l = r.get("lufs")
            print(f"  {r['audio']}  {r['duracao_s']}s  "
                  f"{(str(round(l,1)) + ' LUFS') if l is not None else 'LUFS n/d'}  "
                  f"{len(r['picos_s'])} pico(s)")
    print("\nAgora leia os PNG de onda junto com a folha de contatos do vídeo — "
          "é o cruzamento entre batida e corte que vira diretriz.")


if __name__ == "__main__":
    main()
