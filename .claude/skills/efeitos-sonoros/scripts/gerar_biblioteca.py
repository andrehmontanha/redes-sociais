#!/usr/bin/env python3
"""Sintetiza a biblioteca base de efeitos sonoros e trilhas — obra própria,
gerada por código, sem direitos de terceiros.

Uso:
    python gerar_biblioteca.py              # (re)gera tudo em ../biblioteca/
    python gerar_biblioteca.py --so sfx     # só efeitos

É determinístico (semente fixa): rodar de novo produz os mesmos arquivos, então
a biblioteca pode ser regenerada em qualquer máquina em vez de depender de
download. Sons de terceiros (Pixabay, Freesound CC0, licença comprada) entram
pelo `catalogo.py adicionar`, nunca por aqui.
"""

import argparse
import json
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
RAIZ = Path(__file__).resolve().parent.parent / "biblioteca"
rng = np.random.default_rng(20260929)


# ---------------------------------------------------------------- primitivas

def t(dur):
    return np.arange(int(SR * dur)) / SR


def env_ad(n, ataque, decaimento_curva=4.0):
    a = max(1, int(n * ataque))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a) ** 2
    e[a:] = np.exp(-decaimento_curva * np.linspace(0, 1, n - a))
    return e


def ruido(n):
    return rng.standard_normal(n)


def biquad_bp(x, freqs, q=2.0):
    """Passa-faixa com frequência central variando no tempo (RBJ cookbook)."""
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    freqs = np.broadcast_to(freqs, x.shape)
    for i in range(len(x)):
        w0 = 2 * np.pi * min(freqs[i], SR * 0.45) / SR
        alpha = np.sin(w0) / (2 * q)
        b0, b2 = alpha, -alpha
        a0, a1, a2 = 1 + alpha, -2 * np.cos(w0), 1 - alpha
        yi = (b0 * x[i] + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x[i], y1, yi
        y[i] = yi
    return y


def passa_baixa(x, corte):
    a = np.exp(-2 * np.pi * corte / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def passa_alta(x, corte):
    return x - passa_baixa(x, corte)


def seno_varrido(f0, f1, dur, curva="exp"):
    tt = t(dur)
    if curva == "exp":
        f = f0 * (f1 / f0) ** (tt / dur)
    else:
        f = np.linspace(f0, f1, len(tt))
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def saturar(x, drive=1.5):
    return np.tanh(drive * x) / np.tanh(drive)


def normalizar(x, pico_db=-1.0):
    p = np.max(np.abs(x)) or 1
    return x / p * 10 ** (pico_db / 20)


def fade(x, ini=0.002, fim=0.01):
    x = x.copy()
    a, b = int(SR * ini), int(SR * fim)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def estereo(x, largura=0.0):
    if largura <= 0:
        return np.stack([x, x], 1)
    atraso = int(SR * 0.012 * largura)
    d = np.concatenate([np.zeros(atraso), x[:-atraso]]) if atraso else x
    return np.stack([x, 0.8 * x + 0.2 * d], 1)


def gravar_wav(caminho: Path, x):
    if x.ndim == 1:
        x = estereo(x)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- efeitos

def whoosh(dur=0.7, f0=300, f1=3200, q=1.6):
    n = int(SR * dur)
    meio = n // 2
    freqs = np.concatenate([np.geomspace(f0, f1, meio), np.geomspace(f1, f0 * 1.5, n - meio)])
    x = biquad_bp(ruido(n), freqs, q)
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.6
    return fade(normalizar(x * e, -3))


def pop():
    x = seno_varrido(900, 180, 0.09) * env_ad(int(SR * 0.09), 0.02, 6)
    return fade(normalizar(x, -2), 0.0005, 0.005)


def clique():
    n = int(SR * 0.025)
    x = passa_alta(ruido(n), 2500) * np.exp(-np.linspace(0, 30, n))
    x += 0.4 * np.sin(2 * np.pi * 3200 * t(0.025)) * np.exp(-np.linspace(0, 40, n))
    return fade(normalizar(x, -3), 0.0002, 0.003)


def digitacao(toques=9, dur=1.2):
    x = np.zeros(int(SR * dur))
    posicoes = np.sort(rng.uniform(0.02, dur - 0.05, toques))
    for p in posicoes:
        c = clique() * rng.uniform(0.5, 1.0)
        i = int(p * SR)
        x[i:i + len(c)] += c[: len(x) - i]
    return normalizar(x, -4)


def ding(f=1320, dur=1.6):
    tt = t(dur)
    x = sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt * d)
            for r, a, d in [(1, 1, 2.5), (2.76, 0.45, 4), (5.4, 0.25, 7), (8.9, 0.1, 10)])
    return fade(normalizar(x * env_ad(len(tt), 0.003, 0.1), -3), 0.001, 0.05)


def impacto_grave(dur=1.4):
    n = int(SR * dur)
    corpo = seno_varrido(140, 42, dur) * np.exp(-np.linspace(0, 5, n))
    transiente = passa_baixa(ruido(n), 1800) * np.exp(-np.linspace(0, 60, n))
    return fade(normalizar(saturar(corpo + 0.6 * transiente, 2.2), -1), 0.0005, 0.05)


def hit_seco():
    n = int(SR * 0.3)
    corpo = np.sin(2 * np.pi * 180 * t(0.3)) * np.exp(-np.linspace(0, 12, n))
    ruido_curto = passa_baixa(ruido(n), 4000) * np.exp(-np.linspace(0, 35, n))
    return fade(normalizar(saturar(corpo + 0.8 * ruido_curto, 1.8), -1), 0.0003, 0.02)


def riser(dur=2.0):
    n = int(SR * dur)
    x = biquad_bp(ruido(n), np.geomspace(400, 7000, n), 3.0)
    x += 0.35 * seno_varrido(220, 1760, dur)
    e = np.linspace(0, 1, n) ** 2.2
    return fade(normalizar(x * e, -3), 0.01, 0.004)


def glitch(dur=0.35):
    n = int(SR * dur)
    x = np.zeros(n)
    i = 0
    while i < n:
        bloco = int(SR * rng.uniform(0.008, 0.04))
        f = rng.choice([220, 440, 880, 1760, 3520])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(bloco) / SR)) * rng.uniform(0.3, 1)
        if rng.random() < 0.3:
            seg = ruido(bloco) * 0.6
        x[i:i + bloco] = seg[: n - i]
        i += bloco + int(SR * rng.uniform(0, 0.01))
    return fade(normalizar(passa_baixa(x, 6000), -4), 0.001, 0.01)


def obturador():
    x = np.zeros(int(SR * 0.22))
    for p, g in [(0.0, 1.0), (0.09, 0.8)]:
        n = int(SR * 0.04)
        c = passa_alta(ruido(n), 1200) * np.exp(-np.linspace(0, 18, n)) * g
        i = int(p * SR)
        x[i:i + n] += c
    return fade(normalizar(x, -3), 0.0003, 0.01)


def brilho():
    notas = [1568, 2093, 2637, 3136, 4186]
    x = np.zeros(int(SR * 1.3))
    for k, f in enumerate(notas):
        s = np.sin(2 * np.pi * f * t(0.6)) * np.exp(-np.linspace(0, 7, int(SR * 0.6)))
        i = int(SR * 0.07 * k)
        x[i:i + len(s)] += s * (0.9 - 0.1 * k)
    return fade(normalizar(x, -5), 0.001, 0.05)


def notificacao():
    a = np.sin(2 * np.pi * 880 * t(0.12)) * env_ad(int(SR * 0.12), 0.05, 3)
    b = np.sin(2 * np.pi * 1320 * t(0.28)) * env_ad(int(SR * 0.28), 0.03, 5)
    return fade(normalizar(np.concatenate([a, np.zeros(int(SR * 0.03)), b]), -4))


def swipe():
    return whoosh(0.28, 1200, 6000, 2.2)


EFEITOS = {
    # id: (função, categoria, família, uso)
    "whoosh-curto": (lambda: whoosh(0.45), "transicao", "impacto", "troca de cena rápida, texto entrando de lado"),
    "whoosh-longo": (lambda: whoosh(1.1, 200, 2600, 1.3), "transicao", "impacto", "transição lenta, mudança de bloco"),
    "swipe": (swipe, "transicao", "sutil", "deslize de card, troca de slide"),
    "swoosh-reverso": (lambda: whoosh(0.8)[::-1].copy(), "transicao", "impacto", "antes de um corte seco ou revelação"),
    "riser": (riser, "tensao", "impacto", "subida antes do gancho ou do CTA"),
    "impacto-grave": (impacto_grave, "impacto", "impacto", "revelação, número grande, logo final"),
    "hit-seco": (hit_seco, "impacto", "impacto", "texto que entra batendo, corte no beat"),
    "pop": (pop, "ui", "sutil", "elemento aparecendo, bolha, emoji"),
    "clique": (clique, "ui", "sutil", "botão, seleção, item de lista"),
    "digitacao": (digitacao, "ui", "sutil", "texto sendo digitado na tela"),
    "notificacao": (notificacao, "ui", "sutil", "mensagem, alerta, novidade"),
    "ding": (ding, "destaque", "sutil", "acerto, check, dica"),
    "brilho": (brilho, "destaque", "sutil", "produto em destaque, antes/depois, brilho"),
    "obturador": (obturador, "foto", "sutil", "foto congelando, bastidor"),
    "glitch": (glitch, "transicao", "impacto", "erro proposital, virada de tom"),
}


# ---------------------------------------------------------------- trilhas

def kick():
    return seno_varrido(150, 45, 0.35) * np.exp(-np.linspace(0, 7, int(SR * 0.35)))


def hat():
    n = int(SR * 0.05)
    return passa_alta(ruido(n), 7000) * np.exp(-np.linspace(0, 25, n)) * 0.25


def pad(freqs, dur, brilho_corte=1800):
    tt = t(dur)
    x = sum(sum(np.sin(2 * np.pi * f * h * tt + rng.uniform(0, 6)) / h ** 1.3 for h in (1, 2, 3))
            for f in freqs)
    x = passa_baixa(x, brilho_corte)
    a = int(SR * 0.4)
    e = np.ones(len(tt))
    e[:a] = np.linspace(0, 1, a)
    e[-a:] = np.linspace(1, 0, a)
    return x * e


ACORDES = {  # I–V–vi–IV em Dó
    "C": [261.63, 329.63, 392.00], "G": [196.00, 246.94, 293.66],
    "Am": [220.00, 261.63, 329.63], "F": [174.61, 220.00, 261.63],
}


def trilha(bpm, compassos, bateria="leve", corte_pad=1800):
    batida = 60 / bpm
    dur = compassos * 4 * batida
    x = np.zeros(int(SR * dur) + SR)
    progressao = ["C", "G", "Am", "F"]
    for c in range(compassos):
        ini = int(SR * c * 4 * batida)
        p = pad(ACORDES[progressao[c % 4]], 4 * batida, corte_pad) * 0.18
        x[ini:ini + len(p)] += p
        baixo = np.sin(2 * np.pi * ACORDES[progressao[c % 4]][0] / 2 * t(4 * batida)) * 0.22
        x[ini:ini + len(baixo)] += baixo * env_ad(len(baixo), 0.02, 1.2)
        if bateria == "nenhuma":
            continue
        for b in range(4):
            pos = ini + int(SR * b * batida)
            if bateria == "energetica" or b in (0, 2):
                k = kick() * 0.9
                x[pos:pos + len(k)] += k
            for sub in ((0.5,) if bateria == "leve" else (0.25, 0.5, 0.75)):
                h = hat()
                q = pos + int(SR * sub * batida)
                x[q:q + len(h)] += h
    x = x[: int(SR * dur)]
    return fade(normalizar(saturar(x, 1.2), -1.5), 0.01, 0.8)


TRILHAS = {
    "pulso-leve-100bpm": (lambda: trilha(100, 16, "leve"), "leve", 100, "institucional, dicas, bastidores"),
    "energetico-124bpm": (lambda: trilha(124, 16, "energetica", 2600), "energetico", 124, "oferta, lançamento, antes/depois rápido"),
    "ambiente-calmo": (lambda: trilha(72, 8, "nenhuma", 1200), "calmo", 72, "bem-estar, hospitalidade, depoimento"),
}


# ---------------------------------------------------------------- main

def registrar(catalogo, item):
    catalogo["itens"] = [i for i in catalogo["itens"] if i["id"] != item["id"]] + [item]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--so", choices=["sfx", "trilhas"])
    a = ap.parse_args()

    arq_cat = RAIZ / "catalogo.json"
    catalogo = json.loads(arq_cat.read_text(encoding="utf-8")) if arq_cat.exists() else {"itens": []}
    licenca = {"tipo": "propria", "descricao": "sintetizado por gerar_biblioteca.py — obra própria, sem direitos de terceiros",
               "credito_obrigatorio": False}

    if a.so in (None, "sfx"):
        for id_, (fn, cat, fam, uso) in EFEITOS.items():
            x = fn()
            arq = RAIZ / "sfx" / f"{id_}.wav"
            gravar_wav(arq, estereo(x, 0.5))
            registrar(catalogo, {"id": id_, "tipo": "sfx", "arquivo": f"sfx/{id_}.wav", "categoria": cat,
                                 "familia": fam, "duracao_s": round(len(x) / SR, 3), "uso": uso, "licenca": licenca})
            print(f"sfx     {id_:18s} {len(x) / SR:5.2f}s")

    if a.so in (None, "trilhas"):
        ffmpeg = shutil.which("ffmpeg")
        for id_, (fn, clima, bpm, uso) in TRILHAS.items():
            x = fn()
            wav = RAIZ / "trilhas" / f"{id_}.wav"
            gravar_wav(wav, estereo(x, 1.0))
            final = wav
            if ffmpeg:  # AAC para o repositório não pesar; o WAV some
                final = wav.with_suffix(".m4a")
                subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "aac",
                                "-b:a", "192k", str(final)], check=True)
                wav.unlink()
            registrar(catalogo, {"id": id_, "tipo": "trilha", "arquivo": f"trilhas/{final.name}", "clima": clima,
                                 "bpm": bpm, "duracao_s": round(len(x) / SR, 2), "uso": uso,
                                 "loop": True, "licenca": licenca})
            print(f"trilha  {id_:18s} {len(x) / SR:5.1f}s  {bpm} bpm")

    catalogo["itens"].sort(key=lambda i: (i["tipo"], i["id"]))
    arq_cat.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"catálogo: {arq_cat} ({len(catalogo['itens'])} itens)")


if __name__ == "__main__":
    main()
