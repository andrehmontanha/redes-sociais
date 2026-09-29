#!/usr/bin/env python3
"""Triagem dos vídeos do perfil para o programa de avatares — SEM biometria.

Uso:
    python triagem_videos.py --cliente <handle> [--pasta clientes/<h>/referencias/cliente/videos] [--folhas 8]

Mede, por vídeo: duração, presença de áudio, fração do tempo com voz (energia na
faixa da fala), número de cortes. Ranqueia quem parece "uma pessoa falando para a
câmera, sem cortes" — o tipo de material que (a) revela quem são os rostos
recorrentes da marca e (b) às vezes serve de treino para o digital twin.

Não detecta, recorta nem compara rostos. Quem identifica as pessoas é o cliente,
olhando as folhas de contato — assim nada biométrico é processado antes de haver
consentimento.

Saída: clientes/<handle>/avatares/triagem.md e folhas de contato em avatares/triagem/.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = Path(os.environ.get("ESTUDIO_RAIZ", AQUI.parents[3]))
ANALISAR = AQUI.parents[1] / "analise-perfil-instagram" / "scripts" / "analisar_video.py"


def sondar(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(arq)],
                       capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def fala(arq):
    """Fração de janelas de 30 ms com energia de voz (300–3400 Hz) dominante."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                       capture_output=True)
    x = np.frombuffer(r.stdout, dtype="<i2").astype(np.float32) / 32768
    if len(x) < 16000:
        return 0.0
    n = 480
    quadros = x[: len(x) // n * n].reshape(-1, n)
    espectro = np.abs(np.fft.rfft(quadros * np.hanning(n), axis=1)) ** 2
    freqs = np.fft.rfftfreq(n, 1 / 16000)
    voz = espectro[:, (freqs >= 300) & (freqs <= 3400)].sum(1)
    total = espectro.sum(1) + 1e-9
    energia = quadros.std(1)
    ativo = energia > max(0.01, np.percentile(energia, 30))
    return float(((voz / total > 0.6) & ativo).mean())


def cortes(arq):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(arq), "-vf", "select='gt(scene,0.3)',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True)
    return r.stderr.count("pts_time:")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--pasta", type=Path)
    ap.add_argument("--folhas", type=int, default=8, help="quantos vídeos ganham folha de contato")
    a = ap.parse_args()
    pasta = a.pasta or RAIZ / "clientes" / a.cliente / "referencias" / "cliente" / "videos"
    videos = sorted(p for p in pasta.glob("*") if p.suffix.lower() in {".mp4", ".mov", ".webm"})
    if not videos:
        sys.exit(f"nenhum vídeo em {pasta} — sincronize a conta (conectar-instagram) primeiro")

    linhas = []
    for v in videos:
        info = sondar(v)
        dur = float(info.get("format", {}).get("duration", 0))
        tem_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
        voz = fala(v) if tem_audio else 0.0
        n_cortes = cortes(v)
        por_10s = n_cortes / max(dur, 1) * 10
        apto = 15 <= dur <= 600 and voz >= 0.45 and por_10s <= 1
        nota = voz * 2 - min(por_10s, 5) * 0.3 + min(dur, 120) / 120
        linhas.append({"arquivo": v.name, "duracao": round(dur, 1), "voz": round(voz, 2), "cortes": n_cortes,
                       "cortes_10s": round(por_10s, 1), "apto_treino": apto, "nota": round(nota, 2)})
    linhas.sort(key=lambda l: -l["nota"])

    saida = RAIZ / "clientes" / a.cliente / "avatares"
    folhas = saida / "triagem"
    folhas.mkdir(parents=True, exist_ok=True)
    for l in linhas[: a.folhas]:
        destino = folhas / Path(l["arquivo"]).stem
        subprocess.run([sys.executable, str(ANALISAR), str(pasta / l["arquivo"]), "--saida", str(destino),
                        "--max-frames", "6"], capture_output=True)
        l["folha"] = str((destino / "contact-sheet.jpg").relative_to(saida))

    md = [f"# Triagem de vídeos — @{a.cliente}", "",
          "Ordem: mais fala contínua e menos cortes primeiro. **Nenhuma análise de rosto foi feita.**",
          "Mostre as folhas ao cliente e pergunte quem aparece, qual o papel e se quer convidar a pessoa.",
          "Hóspedes, clientes e crianças não são candidatos.", "",
          "| vídeo | duração | voz | cortes/10 s | serve de treino? | folha |", "|---|---|---|---|---|---|"]
    for l in linhas:
        md.append(f"| {l['arquivo']} | {l['duracao']} s | {l['voz']:.0%} | {l['cortes_10s']} | "
                  f"{'sim, se a pessoa consentir' if l['apto_treino'] else 'não'} | {l.get('folha', '—')} |")
    md += ["", "Treino ideal continua sendo a gravação dedicada (references/gravacao.md)."]
    (saida / "triagem.md").write_text("\n".join(md), encoding="utf-8")
    aptos = sum(l["apto_treino"] for l in linhas)
    print(f"✓ {len(linhas)} vídeo(s) triados · {aptos} com perfil de material de treino · {saida / 'triagem.md'}")


if __name__ == "__main__":
    main()
