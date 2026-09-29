#!/usr/bin/env python3
"""Confere um vídeo contra as especificações de Reels da Instagram Graph API e
contra o padrão de entrega do estúdio. Código de saída 1 = não publicar.

Uso:
    python validar_reel.py reel.mp4 [--story]

Especificação (Graph API, media_type=REELS / STORIES):
    contêiner MOV/MP4 com moov no início (faststart)
    vídeo H.264 ou HEVC, varredura progressiva, croma 4:2:0, 23–60 fps,
          largura ≤ 1920 px, bitrate ≤ 25 Mbps
    áudio AAC, ≤ 48 kHz, 1–2 canais, ≤ 128 kbps
    duração: Reels 3 s – 15 min · Stories 3 – 60 s
    tamanho: ≤ 300 MB (Reels) · ≤ 100 MB (Stories)
Padrão do estúdio (aviso, não bloqueio):
    9:16 exato em 1080×1920, 30 fps, loudness −14 LUFS ±1,5, ≤ 90 s
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def sondar(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(arq)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def moov_no_inicio(arq):
    with open(arq, "rb") as f:
        cabeca = f.read(64 * 1024)
    i_moov, i_mdat = cabeca.find(b"moov"), cabeca.find(b"mdat")
    return i_moov != -1 and (i_mdat == -1 or i_moov < i_mdat)


def loudness(arq):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(arq), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    linhas = [l for l in r.stderr.splitlines() if l.strip().startswith("I:")]
    return float(linhas[-1].split()[1]) if linhas else None


def fracao(txt):
    a, b = txt.split("/")
    return float(a) / float(b) if float(b) else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--story", action="store_true")
    a = ap.parse_args()

    info = sondar(a.video)
    fmt = info["format"]
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    erros, avisos = [], []
    dur = float(fmt["duration"])
    tamanho_mb = int(fmt["size"]) / 1_048_576

    if not v:
        sys.exit("✗ sem trilha de vídeo")
    if v["codec_name"] not in ("h264", "hevc"):
        erros.append(f"codec de vídeo {v['codec_name']} (precisa H.264 ou HEVC)")
    if v.get("pix_fmt") not in ("yuv420p", "yuvj420p", "yuv420p10le"):
        erros.append(f"croma {v.get('pix_fmt')} (precisa 4:2:0)")
    if v.get("field_order") not in (None, "progressive", "unknown"):
        erros.append(f"vídeo entrelaçado ({v['field_order']})")
    fps = fracao(v.get("avg_frame_rate") or v["r_frame_rate"])
    if not 23 <= fps <= 60:
        erros.append(f"{fps:.2f} fps (precisa 23–60)")
    if int(v["width"]) > 1920:
        erros.append(f"largura {v['width']} px (máx. 1920)")
    br = int(v.get("bit_rate") or 0)
    if br > 25_000_000:
        erros.append(f"bitrate de vídeo {br / 1e6:.1f} Mbps (máx. 25)")
    if not moov_no_inicio(a.video):
        erros.append("moov no fim do arquivo — regrave com -movflags +faststart")

    if au:
        if au["codec_name"] != "aac":
            erros.append(f"áudio {au['codec_name']} (precisa AAC)")
        if int(au.get("sample_rate", 0)) > 48000:
            erros.append(f"áudio a {au['sample_rate']} Hz (máx. 48 kHz)")
        if int(au.get("channels", 0)) > 2:
            erros.append(f"{au['channels']} canais de áudio (máx. 2)")
        abr = int(au.get("bit_rate") or 0)
        if abr > 132_000:
            erros.append(f"áudio a {abr // 1000} kbps (máx. 128)")
        lufs = loudness(a.video)
        if lufs is not None and abs(lufs + 14) > 1.5:
            avisos.append(f"loudness {lufs:.1f} LUFS (alvo −14 ±1,5) — passe pelo mixar_sfx.py")
    else:
        avisos.append("vídeo sem áudio — Reel mudo perde alcance; sonorize com efeitos-sonoros")

    lim_dur, lim_mb = ((3, 60), 100) if a.story else ((3, 900), 300)
    if not lim_dur[0] <= dur <= lim_dur[1]:
        erros.append(f"duração {dur:.1f}s (precisa {lim_dur[0]}–{lim_dur[1]} s)")
    if tamanho_mb > lim_mb:
        erros.append(f"{tamanho_mb:.0f} MB (máx. {lim_mb} MB)")

    if (int(v["width"]), int(v["height"])) != (1080, 1920):
        avisos.append(f"{v['width']}×{v['height']} — padrão do estúdio é 1080×1920 (9:16)")
    if abs(fps - 30) > 0.5:
        avisos.append(f"{fps:.2f} fps — padrão do estúdio é 30")
    if not a.story and dur > 90:
        avisos.append(f"{dur:.0f}s — acima de 90 s o Reel perde distribuição na aba Reels")

    print(f"{a.video.name}: {v['width']}×{v['height']} {v['codec_name']} {fps:.0f} fps · {dur:.1f}s · "
          f"{tamanho_mb:.1f} MB · áudio {au['codec_name'] + ' ' + str(int(au.get('bit_rate') or 0) // 1000) + ' kbps' if au else 'nenhum'}")
    for e in erros:
        print("✗", e)
    for w in avisos:
        print("!", w)
    if not erros:
        print("✓ dentro da especificação da API")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
