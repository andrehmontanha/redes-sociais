#!/usr/bin/env python3
"""Mede a identidade visual de um perfil a partir das imagens do próprio cliente
e grava o rascunho do brand kit.

Uso:
    # medir e gerar o rascunho
    python extrair_identidade.py clientes/<handle>/referencias/cliente/ \\
        --handle <handle> --saida clientes/<handle>/brand-kit.json

    # conferir um brand kit já preenchido (código de saída 1 se incompleto)
    python extrair_identidade.py --validar clientes/<handle>/brand-kit.json

O que o script MEDE (origem "medido"):
    - paleta dominante por k-means em espaço Lab-aproximado, com peso por área
    - papéis sugeridos: fundo, primaria, destaque, texto — o texto é escolhido
      pelo maior contraste WCAG contra o fundo
    - tratamento de foto: brilho, contraste, saturação e temperatura médios

O que o script NÃO mede, e deixa marcado como pendente para quem olhar as
referências com `Read`: tipografia, tom de voz, composição, elementos gráficos
recorrentes. Não existe detecção confiável de fonte a partir de foto de feed —
chutar aqui contamina todos os criativos que vêm depois.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

EXTS = {".jpg", ".jpeg", ".png", ".webp"}
PENDENTE = "PENDENTE"


# ---------------------------------------------------------------- cor

def hex_de(rgb):
    return "#{:02x}{:02x}{:02x}".format(*[int(round(c)) for c in rgb])


def rgb_de(hexcor):
    h = hexcor.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminancia(rgb):
    def canal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def saturacao(rgb):
    mx, mn = max(rgb) / 255, min(rgb) / 255
    return 0 if mx == 0 else (mx - mn) / mx


def kmeans(pixels, k, iteracoes=25, semente=7):
    rng = np.random.default_rng(semente)
    centros = pixels[rng.choice(len(pixels), k, replace=False)]
    for _ in range(iteracoes):
        dist = ((pixels[:, None, :] - centros[None, :, :]) ** 2).sum(-1)
        rotulo = dist.argmin(1)
        novos = np.array([pixels[rotulo == i].mean(0) if (rotulo == i).any() else centros[i]
                          for i in range(k)])
        if np.allclose(novos, centros, atol=0.5):
            break
        centros = novos
    pesos = np.bincount(rotulo, minlength=k) / len(pixels)
    return centros, pesos


# ---------------------------------------------------------------- medição

def carregar(pasta: Path, lado=160):
    arquivos = sorted(p for p in pasta.rglob("*") if p.suffix.lower() in EXTS)
    if not arquivos:
        sys.exit(f"nenhuma imagem em {pasta} — rode a captura de assets da análise antes")
    amostras, tratamentos = [], []
    for arq in arquivos:
        img = Image.open(arq).convert("RGB")
        img.thumbnail((lado, lado))
        px = np.asarray(img, dtype=np.float64).reshape(-1, 3)
        amostras.append(px)
        cinza = px @ [0.299, 0.587, 0.114]
        mx, mn = px.max(1), px.min(1)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
        tratamentos.append({
            "brilho": cinza.mean() / 255,
            "contraste": cinza.std() / 128,
            "saturacao": sat.mean(),
            "temperatura": (px[:, 0].mean() - px[:, 2].mean()) / 255,
        })
    return arquivos, np.vstack(amostras), tratamentos


def paleta(pixels, k):
    # descarta quase-preto e quase-branco puros do k-means: eles dominam por área
    # em fotos e engolem as cores de marca; entram depois como candidatos a texto
    cinza = pixels @ [0.299, 0.587, 0.114]
    uteis = pixels[(cinza > 18) & (cinza < 240)]
    if len(uteis) < k * 50:
        uteis = pixels
    if len(uteis) > 60000:
        uteis = uteis[np.random.default_rng(1).choice(len(uteis), 60000, replace=False)]
    centros, pesos = kmeans(uteis, k)
    ordem = np.argsort(-pesos)
    return [(tuple(centros[i]), float(pesos[i])) for i in ordem]


def atribuir_papeis(cores):
    """Sugere papéis. É sugestão: quem confirma é o humano olhando o feed."""
    fundo = cores[0][0]
    restantes = cores[1:]
    primaria = max(restantes, key=lambda c: saturacao(c[0]) * (0.5 + c[1]))[0]
    destaque_cands = [c for c in restantes if c[0] != primaria]
    destaque = max(destaque_cands, key=lambda c: contraste(c[0], fundo) + saturacao(c[0]))[0] \
        if destaque_cands else primaria
    candidatos_texto = [c[0] for c in cores] + [(17, 17, 17), (255, 255, 255)]
    texto = max(candidatos_texto, key=lambda c: contraste(c, fundo))
    return {
        "fundo": hex_de(fundo),
        "primaria": hex_de(primaria),
        "destaque": hex_de(destaque),
        "texto": hex_de(texto),
    }


def descrever_tratamento(t):
    def rotulo(v, faixas):
        for limite, nome in faixas:
            if v < limite:
                return nome
        return faixas[-1][1]
    return {
        "brilho": round(t["brilho"], 3),
        "contraste": round(t["contraste"], 3),
        "saturacao": round(t["saturacao"], 3),
        "temperatura": round(t["temperatura"], 3),
        "leitura": ", ".join([
            rotulo(t["brilho"], [(0.35, "escuro"), (0.6, "médio"), (9, "claro")]),
            rotulo(t["saturacao"], [(0.2, "dessaturado"), (0.4, "natural"), (9, "saturado")]),
            rotulo(t["temperatura"], [(-0.03, "frio"), (0.05, "neutro"), (9, "quente")]),
            rotulo(t["contraste"], [(0.35, "baixo contraste"), (0.55, "contraste médio"), (9, "alto contraste")]),
        ]),
    }


def medir(pasta: Path, handle: str, k: int):
    arquivos, pixels, tratamentos = carregar(pasta)
    cores = paleta(pixels, k)
    papeis = atribuir_papeis(cores)
    media = {chave: float(np.mean([t[chave] for t in tratamentos])) for chave in tratamentos[0]}
    fundo, texto = rgb_de(papeis["fundo"]), rgb_de(papeis["texto"])
    return {
        "handle": handle,
        "versao": 1,
        "gerado_em": date.today().isoformat(),
        "confirmado_por": None,
        "fontes_da_medicao": {"pasta": str(pasta), "imagens": len(arquivos)},
        "cores": {
            "origem": "medido",
            "papeis": papeis,
            "contraste_texto_fundo": round(contraste(texto, fundo), 2),
            "paleta": [{"hex": hex_de(c), "peso": round(p, 3)} for c, p in cores],
        },
        "tratamento_foto": {"origem": "medido", **descrever_tratamento(media)},
        "tipografia": {
            "origem": PENDENTE,
            "titulo": {"familia": PENDENTE, "peso": 700, "caixa": "normal", "google_fonts": True},
            "texto": {"familia": PENDENTE, "peso": 400, "google_fonts": True},
            "observacao": "nomeie a fonte do Google Fonts mais próxima do que o feed usa",
        },
        "composicao": {
            "origem": PENDENTE,
            "alinhamento": PENDENTE,
            "margem_px": 72,
            "raio_borda_px": 0,
            "texto_sobre_foto": PENDENTE,
            "densidade_texto": PENDENTE,
        },
        "elementos": {
            "origem": PENDENTE,
            "logo": None,
            "assinatura": PENDENTE,
            "recorrentes": [],
        },
        "voz": {
            "origem": PENDENTE,
            "tom": PENDENTE,
            "pessoa": PENDENTE,
            "emojis": PENDENTE,
            "hashtags_fixas": [],
            "cta_preferido": PENDENTE,
            "palavras_evitar": [],
        },
        "video": {
            "origem": PENDENTE,
            "ritmo_corte_s": None,
            "legenda_na_tela": PENDENTE,
            "estilo_movimento": PENDENTE,
            "sfx_familia": PENDENTE,
        },
        "referencias_aprovadas": [],
    }


# ---------------------------------------------------------------- validação

def pendencias(no, caminho=""):
    if isinstance(no, dict):
        for k, v in no.items():
            yield from pendencias(v, f"{caminho}.{k}" if caminho else k)
    elif isinstance(no, list):
        for i, v in enumerate(no):
            yield from pendencias(v, f"{caminho}[{i}]")
    elif no == PENDENTE:
        yield caminho


def validar(arq: Path) -> int:
    kit = json.loads(arq.read_text(encoding="utf-8"))
    erros = [f"campo pendente: {p}" for p in pendencias(kit)]
    papeis = kit.get("cores", {}).get("papeis", {})
    try:
        c = contraste(rgb_de(papeis["texto"]), rgb_de(papeis["fundo"]))
        if c < 4.5:
            erros.append(f"contraste texto/fundo {c:.2f} abaixo de 4.5 (WCAG AA) — legenda some no celular")
    except (KeyError, ValueError):
        erros.append("cores.papeis precisa de 'texto' e 'fundo' em hex")
    if "destaque" in papeis:
        sobre = papeis.get("texto_sobre_destaque", papeis.get("fundo"))
        try:
            c = contraste(rgb_de(sobre), rgb_de(papeis["destaque"]))
            if c < 3:
                erros.append(f"contraste do botão (texto {sobre} sobre destaque {papeis['destaque']}) {c:.2f} "
                             "abaixo de 3 — defina cores.papeis.texto_sobre_destaque")
        except (KeyError, ValueError):
            pass
    for r in kit.get("elementos", {}).get("recorrentes", []) or []:
        if re.search(r"contador|barra de progresso|\b\d{1,2}\s*/\s*\d{1,2}\b", str(r), re.I):
            erros.append(f"elementos.recorrentes com contagem ('{r}') — regra do estúdio: nenhuma contagem nas peças")
    if not kit.get("confirmado_por"):
        erros.append("confirmado_por vazio — o brand kit só vale depois que um humano confirma")
    if len(kit.get("referencias_aprovadas", [])) < 3:
        erros.append("referencias_aprovadas: mínimo 3 posts do próprio perfil que representam a marca")
    for e in erros:
        print("✗", e)
    if not erros:
        print("✓ brand kit completo e confirmado")
    return 1 if erros else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", nargs="?", type=Path, help="imagens do próprio cliente")
    ap.add_argument("--handle")
    ap.add_argument("--saida", type=Path)
    ap.add_argument("--cores", type=int, default=6, help="tamanho da paleta (padrão 6)")
    ap.add_argument("--validar", type=Path, help="brand-kit.json a conferir")
    a = ap.parse_args()

    if a.validar:
        sys.exit(validar(a.validar))
    if not (a.pasta and a.handle and a.saida):
        ap.error("informe pasta, --handle e --saida (ou --validar)")
    if a.saida.exists():
        sys.exit(f"{a.saida} já existe — brand kit confirmado não se sobrescreve. "
                 "Grave em outro caminho e compare, ou apague de propósito.")
    kit = medir(a.pasta, a.handle, a.cores)
    a.saida.parent.mkdir(parents=True, exist_ok=True)
    a.saida.write_text(json.dumps(kit, ensure_ascii=False, indent=2), encoding="utf-8")
    p = kit["cores"]["papeis"]
    print(f"rascunho gravado em {a.saida}")
    print(f"  papéis: fundo {p['fundo']} · primária {p['primaria']} · destaque {p['destaque']} · texto {p['texto']}")
    print(f"  contraste texto/fundo: {kit['cores']['contraste_texto_fundo']}")
    print(f"  tratamento: {kit['tratamento_foto']['leitura']}")
    print(f"  pendentes: {len(list(pendencias(kit)))} campos — preencha olhando as referências com Read")


if __name__ == "__main__":
    main()
