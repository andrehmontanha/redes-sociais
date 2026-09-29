#!/usr/bin/env python3
"""Aplica trilha e efeitos sonoros num vídeo a partir de uma folha de deixas
(cue sheet) e entrega o áudio masterizado no padrão do Instagram.

Uso:
    python mixar_sfx.py video.mp4 deixas.json --saida final.mp4

deixas.json:
    {
      "trilha": {"id": "pulso-leve-100bpm", "ganho_db": -4, "inicio_s": 0, "fade_out_s": 1.5},
      "manter_audio_original": true,         # voz/som direto do vídeo, se houver
      "ducking": true,                       # abaixa a trilha quando há voz no original
      "deixas": [
        {"t": 0.00, "sfx": "riser",         "ganho_db": -8, "nota": "sobe até o gancho"},
        {"t": 2.00, "sfx": "impacto-grave", "ganho_db": -6, "nota": "gancho aparece"},
        {"t": 3.60, "sfx": "whoosh-curto",  "ganho_db": -10, "nota": "corte para cena 2"}
      ]
    }

O que ele faz:
    - só usa sons registrados no catálogo, com licença válida
    - posiciona cada efeito no tempo exato, com ganho próprio
    - estende ou corta a trilha para a duração do vídeo, com fade de saída
    - normaliza o resultado para -14 LUFS integrado, pico real -1 dBTP
      (o alvo de loudness das plataformas sociais; acima disso o app reduz, abaixo
      o vídeo soa fraco perto dos outros no feed)
    - copia o vídeo sem recomprimir; áudio AAC 128 kbps 48 kHz estéreo (teto da API para Reels)
    - grava <saida>.creditos.txt quando algum som exige crédito na legenda
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "biblioteca"


def ffprobe(arq, *campos):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", ",".join(campos), "-of", "json", str(arq)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def tem_audio(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", str(arq)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("deixas", type=Path)
    ap.add_argument("--saida", type=Path, required=True)
    ap.add_argument("--lufs", type=float, default=-14.0)
    a = ap.parse_args()

    catalogo = {i["id"]: i for i in json.loads((RAIZ / "catalogo.json").read_text(encoding="utf-8"))["itens"]}
    folha = json.loads(a.deixas.read_text(encoding="utf-8"))
    dur = float(ffprobe(a.video, "format=duration")["format"]["duration"])

    def item(id_, tipo):
        if id_ not in catalogo:
            sys.exit(f"som '{id_}' não está no catálogo — `catalogo.py listar` mostra os disponíveis")
        i = catalogo[id_]
        if i["tipo"] != tipo:
            sys.exit(f"'{id_}' é {i['tipo']}, não {tipo}")
        if not i.get("licenca", {}).get("tipo"):
            sys.exit(f"'{id_}' sem licença registrada — não pode ser usado")
        return i

    entradas = ["-i", str(a.video)]
    filtros, rotulos, creditos = [], [], []
    idx = 1

    original = folha.get("manter_audio_original", True) and tem_audio(a.video)
    if original:
        filtros.append("[0:a]aresample=48000,aformat=channel_layouts=stereo[orig]")

    trilha = folha.get("trilha")
    if trilha:
        t = item(trilha["id"], "trilha")
        entradas += ["-stream_loop", "-1", "-i", str(RAIZ / t["arquivo"])]
        ini = float(trilha.get("inicio_s", 0))
        fo = float(trilha.get("fade_out_s", 1.5))
        g = float(trilha.get("ganho_db", -4))
        filtros.append(
            f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur - ini:.3f},"
            f"adelay={int(ini * 1000)}:all=1,afade=t=in:st={ini:.3f}:d=0.3,"
            f"afade=t=out:st={max(0, dur - fo):.3f}:d={fo:.3f},volume={g}dB[trilha]")
        if t["licenca"].get("credito_obrigatorio"):
            creditos.append(t["licenca"]["credito"])
        idx += 1
        if original and folha.get("ducking", True):
            filtros.append("[orig]asplit=2[orig][orig_sc]")
            filtros.append("[trilha][orig_sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[trilha]")
        rotulos.append("[trilha]")
    if original:
        rotulos.append("[orig]")

    for n, d in enumerate(folha.get("deixas", [])):
        s = item(d["sfx"], "sfx")
        if d["t"] >= dur:
            sys.exit(f"deixa em {d['t']}s passa do fim do vídeo ({dur:.2f}s)")
        entradas += ["-i", str(RAIZ / s["arquivo"])]
        filtros.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
                       f"adelay={int(d['t'] * 1000)}:all=1,volume={float(d.get('ganho_db', -8))}dB[s{n}]")
        rotulos.append(f"[s{n}]")
        if s["licenca"].get("credito_obrigatorio"):
            creditos.append(s["licenca"]["credito"])
        idx += 1

    if not rotulos:
        sys.exit("nada para mixar: sem trilha, sem deixas e o vídeo não tem áudio")

    filtros.append(f"{''.join(rotulos)}amix=inputs={len(rotulos)}:normalize=0:dropout_transition=0,"
                   f"atrim=0:{dur:.3f},loudnorm=I={a.lufs}:TP=-1.0:LRA=11,aresample=48000[mix]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *entradas, "-filter_complex", ";".join(filtros),
           "-map", "0:v", "-map", "[mix]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", str(a.saida)]
    subprocess.run(cmd, check=True)

    if creditos:
        a.saida.with_suffix(".creditos.txt").write_text("\n".join(dict.fromkeys(creditos)), encoding="utf-8")
    medido = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(a.saida), "-af", "ebur128=peak=true",
                             "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = [l for l in medido.splitlines() if l.strip().startswith("I:")]
    print(f"mixado: {a.saida} · {len(folha.get('deixas', []))} efeito(s) · "
          f"loudness {lufs[-1].strip() if lufs else '?'}" + (" · créditos exigidos" if creditos else ""))


if __name__ == "__main__":
    main()
