#!/usr/bin/env python3
"""Monta um projeto HyperFrames de Reel (1080x1920) a partir de um roteiro de
cenas e do brand kit do cliente, e propõe a folha de deixas de efeitos sonoros.

Uso:
    python montar_reel.py clientes/<handle>/criativos/<id>/roteiro-video.json
    # depois:
    cd clientes/<handle>/criativos/<id>/video && npx --yes hyperframes@<versão> check
    npx --yes hyperframes@<versão> render -o reel-mudo.mp4

roteiro-video.json:
    {
      "brand_kit": "../../brand-kit.json",
      "trilha": "pulso-leve-100bpm",            # id do catálogo de sons, ou null
      "cenas": [
        {"tipo": "foto",  "midia": "../../referencias/cliente/a.jpg", "duracao": 2.4, "texto": "Gancho aqui"},
        {"tipo": "video", "midia": "../../material-cliente/b.mp4", "inicio_s": 3, "duracao": 3, "texto": "...",
         "som_original": true},                  # leva a voz/som do vídeo para o Reel
        {"tipo": "texto", "rotulo": "você sabia?", "titulo": "38 °C direto da fonte", "duracao": 2.5},
        {"tipo": "avatar", "midia": "../../avatares/<pessoa>/videos/<arquivo>.webm", "fundo": "../../referencias/cliente/c.jpg",
         "texto": "opcional", "enquadramento": "base"},   # duração = a da fala; exige manifesto e consentimento
        {"tipo": "cta",   "titulo": "Reserve pelo link da bio", "duracao": 3}
      ]
    }

Gera, em <pasta do roteiro>/video/:
    index.html          composição HyperFrames (uma timeline GSAP pausada, determinística)
    assets/             mídia do cliente copiada, fontes locais, gsap.min.js local
    package.json        CLI do HyperFrames fixada na versão testada
    hyperframes.json
    deixas.json         proposta de efeitos sonoros por corte (edite antes de mixar)

O estilo de movimento sai de brand-kit.video.estilo_movimento:
    sobrio   — crossfade de 0,35 s, texto sobe com fade, zoom lento na foto
    energico — corte seco, texto entra palavra a palavra com rebote, zoom mais rápido
"""

import argparse
import html
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SKILLS = AQUI.parents[1]
HYPERFRAMES_VERSAO = "0.8.90"
GSAP_VERSAO = "3.14.2"
CACHE = Path.home() / ".cache" / "estudio-social"
LARGURA, ALTURA, FPS = 1080, 1920, 30
# Área segura do Reel: a interface cobre o topo, a base (legenda, áudio) e a
# coluna direita (curtir, comentar, compartilhar).
SEGURO = {"topo": 220, "base": 460, "esquerda": 72, "direita": 170}
PROIBIDO = ("concorrente", "tendencia", "tendência", "estudo")


def modulo(caminho: Path, nome: str):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


render_img = modulo(SKILLS / "criativos-imagem" / "scripts" / "renderizar_criativo.py", "render_img")


def gsap_local() -> Path:
    """gsap.min.js baixado do registro npm uma vez. O CDN não é confiável dentro
    do navegador headless (proxy, firewall), e render não pode depender de rede."""
    destino = CACHE / "gsap" / GSAP_VERSAO / "gsap.min.js"
    if not destino.exists():
        import requests
        url = f"https://registry.npmjs.org/gsap/-/gsap-{GSAP_VERSAO}.tgz"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz") as tgz:
            dados = tgz.extractfile("package/dist/gsap.min.js").read()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(dados)
    return destino


def fontes_locais(kit, pasta_fontes: Path, base_kit: Path) -> str:
    """@font-face apontando para arquivos dentro do projeto (lint do HyperFrames exige)."""
    pasta_fontes.mkdir(parents=True, exist_ok=True)
    css = []
    for papel in ("titulo", "texto"):
        f = kit["tipografia"][papel]
        if f.get("google_fonts", True):
            bloco = render_img.google_font_local(f["familia"], f.get("peso", 400))
            for url in re.findall(r"url\((file://[^)]+)\)", bloco):
                origem = Path(re.sub(r"^file://", "", url).replace("%20", " "))
                nome = f"{papel}-{origem.parent.parent.name}-{origem.name}"
                shutil.copy2(origem, pasta_fontes / nome)
                bloco = bloco.replace(url, f"assets/fontes/{nome}")
            css.append(bloco)
        elif f.get("arquivo"):
            origem = base_kit / f["arquivo"]
            shutil.copy2(origem, pasta_fontes / origem.name)
            css.append(f"@font-face{{font-family:'{f['familia']}';src:url('assets/fontes/{origem.name}');"
                       f"font-weight:{f.get('peso', 400)};}}")
    return "\n".join(css)


def copiar_midia(valor, base: Path, raiz_cliente: Path, pasta_assets: Path, n: int) -> str:
    p = (base / valor).resolve()
    if not p.exists():
        sys.exit(f"mídia não encontrada: {p}")
    if raiz_cliente not in p.parents:
        sys.exit(f"mídia fora da pasta do cliente ({raiz_cliente}): {p}\nReel só usa material do próprio cliente.")
    if any(t in str(p.relative_to(raiz_cliente)).lower() for t in PROIBIDO):
        sys.exit(f"mídia em pasta de referência de terceiros: {p}")
    destino = pasta_assets / f"cena{n:02d}{p.suffix.lower()}"
    shutil.copy2(p, destino)
    return f"assets/{destino.name}"


def sondar_duracao(arq: Path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def conferir_avatar(midia: Path, raiz_cliente: Path) -> str:
    """Vídeo de avatar só entra com o manifesto gerado pelo avatar.py e consentimento válido agora."""
    manifesto = midia.with_suffix(".json")
    if not manifesto.exists():
        sys.exit(f"{midia.name} sem manifesto de avatar — só vídeos gerados por avatar.py gerar entram como avatar")
    pessoa = json.loads(manifesto.read_text(encoding="utf-8"))["pessoa"]
    sys.path.insert(0, str(SKILLS / "avatares" / "scripts"))
    import avatar
    avatar.RAIZ = raiz_cliente.parent.parent
    impedimentos = avatar.verificar_uso(raiz_cliente.name, pessoa)
    if impedimentos:
        sys.exit("avatar sem liberação:\n  " + "\n  ".join(impedimentos))
    return pessoa


def palavras(texto, classe):
    return " ".join(f'<span class="{classe}">{html.escape(w)}</span>' for w in texto.split())


def montar(roteiro_path: Path):
    roteiro = json.loads(roteiro_path.read_text(encoding="utf-8"))
    base = roteiro_path.parent.resolve()
    kit_path = (base / roteiro["brand_kit"]).resolve()
    r = subprocess.run([sys.executable, str(render_img.VALIDADOR), "--validar", str(kit_path)],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("brand kit não validado — nenhum criativo antes disso:\n" + r.stdout)
    kit = json.loads(kit_path.read_text(encoding="utf-8"))
    raiz_cliente = kit_path.parent
    cores, video_kit = kit["cores"]["papeis"], kit.get("video", {})
    energico = video_kit.get("estilo_movimento") == "energico"
    legenda = video_kit.get("legenda_na_tela", "sempre")
    cenas = roteiro["cenas"]
    if not cenas:
        sys.exit("roteiro sem cenas")

    projeto = base / "video"
    # monta numa pasta temporária: se alguma trava recusar no meio do caminho,
    # o projeto anterior continua intacto
    assets = projeto / "assets.montando"
    shutil.rmtree(assets, ignore_errors=True)
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(gsap_local(), assets / "gsap.min.js")
    css_fontes = fontes_locais(kit, assets / "fontes", raiz_cliente)
    logo = None
    if kit["elementos"].get("logo"):
        origem = raiz_cliente / kit["elementos"]["logo"]
        shutil.copy2(origem, assets / f"logo{origem.suffix}")
        logo = f"assets/logo{origem.suffix}"

    blocos, tweens, cortes, textos = [], [], [], []
    som_original = False
    avatares = []
    t = 0.0
    trans = 0.0 if energico else 0.35
    for n, c in enumerate(cenas, 1):
        if c["tipo"] == "avatar" and "duracao" not in c:
            c["duracao"] = round(float(sondar_duracao((base / c["midia"]).resolve())) - float(c.get("inicio_s", 0)), 2)
        dur = float(c["duracao"])
        limite = 60 if c["tipo"] == "avatar" else 15
        if not 0.5 <= dur <= limite:
            sys.exit(f"cena {n}: duração {dur}s fora de 0,5–{limite} s")
        cid = f"cena{n:02d}"
        mostra_texto = c["tipo"] in ("texto", "cta") or legenda == "sempre" or (legenda == "gancho" and n == 1)
        texto = c.get("texto") or c.get("titulo") or ""
        fundo_html = ""
        if c["tipo"] == "foto":
            src = copiar_midia(c["midia"], base, raiz_cliente, assets, n)
            fundo_html = f'<div class="midia" id="{cid}-midia" data-layout-allow-overflow><img src="{src}" alt=""></div>'
            zoom = 1.12 if energico else 1.06
            tweens.append(f'tl.fromTo("#{cid}-midia", {{scale: 1}}, {{scale: {zoom}, duration: {dur + trans}, ease: "none"}}, {t});')
        elif c["tipo"] == "video":
            src = copiar_midia(c["midia"], base, raiz_cliente, assets, n)
            inicio = float(c.get("inicio_s", 0))
            # vídeo não pode ter ancestral com data-start: fica fora da seção, com o próprio tempo
            blocos.append(f'<div class="midia-video"><video id="{cid}-video" src="{src}" data-start="{t:.3f}" '
                          f'data-duration="{dur + trans:.3f}" data-media-start="{inicio:.3f}" data-track-index="0" '
                          f'muted playsinline></video></div>')
            if c.get("som_original"):
                som_original = True
                blocos.append(f'<audio id="{cid}-audio" src="{src}" data-start="{t:.3f}" data-duration="{dur + trans:.3f}" '
                              f'data-media-start="{inicio:.3f}" data-track-index="10" data-volume="1"></audio>')
        elif c["tipo"] == "avatar":
            pessoa = conferir_avatar((base / c["midia"]).resolve(), raiz_cliente)
            avatares.append(pessoa)
            src = copiar_midia(c["midia"], base, raiz_cliente, assets, n)
            inicio = float(c.get("inicio_s", 0))
            if c.get("fundo"):
                fsrc = copiar_midia(c["fundo"], base, raiz_cliente, assets, n + 100)
                fundo_html = f'<div class="midia" id="{cid}-midia" data-layout-allow-overflow><img src="{fsrc}" alt=""></div>'
                tweens.append(f'tl.fromTo("#{cid}-midia", {{scale: 1}}, {{scale: 1.04, duration: {dur + trans}, ease: "none"}}, {t});')
            else:
                fundo_html = '<div class="midia fundo-marca"></div>'
            enquadramento = "avatar-base" if c.get("enquadramento") == "base" else "avatar-cheio"
            som_original = True
            avatar_html = (f'<div class="midia-avatar {enquadramento}"><video id="{cid}-avatar" src="{src}" '
                           f'data-start="{t:.3f}" data-duration="{dur + trans:.3f}" data-media-start="{inicio:.3f}" '
                           f'data-track-index="2" muted playsinline></video></div>'
                           f'<audio id="{cid}-voz" src="{src}" data-start="{t:.3f}" data-duration="{dur:.3f}" '
                           f'data-media-start="{inicio:.3f}" data-track-index="11" data-volume="1"></audio>')
        elif c["tipo"] not in ("texto", "cta"):
            sys.exit(f"cena {n}: tipo '{c['tipo']}' inválido (foto, video, avatar, texto, cta)")

        fundo_solido = c["tipo"] in ("texto", "cta")
        conteudo = ""
        if c.get("rotulo") and mostra_texto:
            conteudo += f'<div class="rotulo" id="{cid}-rotulo">{html.escape(c["rotulo"])}</div>'
        if texto and mostra_texto:
            classe = "titulo grande" if fundo_solido else "titulo"
            conteudo += f'<h1 class="{classe}" id="{cid}-titulo">{palavras(texto, cid + "-p")}</h1>'
            # o gancho já está na tela no quadro 0: é ele que segura a rolagem
            atraso = 0.0 if n == 1 else (0.15 if energico else 0.25)
            textos.append(t + atraso)
        if c["tipo"] == "cta":
            if c.get("subtitulo"):
                conteudo += f'<p class="subtitulo" id="{cid}-sub">{html.escape(c["subtitulo"])}</p>'
            if logo:
                conteudo += f'<img class="logo-cta" id="{cid}-logo" src="{logo}" alt="">'
            elif kit["elementos"].get("assinatura") not in (None, "nenhuma"):
                conteudo += f'<div class="assinatura" id="{cid}-assinatura">{html.escape(kit["elementos"]["assinatura"])}</div>'

        classe_secao = "cena solido" if fundo_solido else ("cena sobre-midia" if c["tipo"] != "video" else "cena sobre-video")
        if c["tipo"] == "avatar":
            # camadas: fundo → avatar (WebM com alfa) → texto. Texto nunca atrás da pessoa.
            blocos.append(f'<section id="{cid}" class="clip cena" data-start="{t:.3f}" data-duration="{dur + trans:.3f}" '
                          f'data-track-index="0">{fundo_html}</section>')
            blocos.append(avatar_html)
            blocos.append(f'<section id="{cid}-textos" class="clip cena cena-avatar" data-start="{t:.3f}" '
                          f'data-duration="{dur + trans:.3f}" data-track-index="3">'
                          f'<div class="texto-area" id="{cid}-area">{conteudo}</div></section>')
        else:
            blocos.append(
                f'<section id="{cid}" class="clip {classe_secao}" data-start="{t:.3f}" data-duration="{dur + trans:.3f}" '
                f'data-track-index="{1 if c["tipo"] == "video" else 0}">{fundo_html}'
                f'{"<div class=veu></div>" if fundo_html or c["tipo"] == "video" else ""}'
                f'<div class="texto-area" id="{cid}-area">{conteudo}</div></section>')

        if trans and n > 1:
            # crossfade: a cena nova entra inteira e o texto da anterior sai junto,
            # para nunca haver dois textos sobrepostos na transição
            tweens.append(f'tl.fromTo("#{cid}", {{opacity: 0}}, {{opacity: 1, duration: {trans}}}, {t});')
            tweens.append(f'tl.to("#cena{n - 1:02d}-area", {{opacity: 0, duration: {trans * 0.6:.3f}}}, {t});')
        if texto and mostra_texto:
            if n == 1:
                # gancho: 100% legível no quadro 0; só um "punch" de escala, sem fade
                tweens.append(f'tl.fromTo("#{cid}-titulo", {{scale: {1.1 if energico else 1.04}}}, {{scale: 1, '
                              f'duration: 0.45, ease: "power2.out", transformOrigin: "left bottom"}}, {t});')
            elif energico:
                tweens.append(f'tl.fromTo(".{cid}-p", {{opacity: 0, scale: 0.6, y: 30}}, {{opacity: 1, scale: 1, y: 0, '
                              f'duration: 0.35, ease: "back.out(2)", stagger: 0.07}}, {t + atraso});')
            else:
                tweens.append(f'tl.fromTo("#{cid}-titulo", {{opacity: 0, y: 40}}, {{opacity: 1, y: 0, '
                              f'duration: 0.6, ease: "power3.out"}}, {t + atraso});')
        if c.get("rotulo") and mostra_texto:
            tweens.append(f'tl.fromTo("#{cid}-rotulo", {{opacity: 0, y: 20}}, {{opacity: 1, y: 0, duration: 0.4}}, {t + 0.1});')
        if c["tipo"] == "cta":
            alvo = f"#{cid}-logo" if logo else f"#{cid}-assinatura"
            tweens.append(f'tl.fromTo("{alvo}", {{opacity: 0, y: 24}}, {{opacity: 1, y: 0, duration: 0.5}}, {t + 0.6});')
        if n > 1:
            cortes.append(t)
        t += dur

    duracao = round(t + trans, 3)
    if duracao < 3:
        sys.exit(f"Reel com {duracao}s — mínimo de 3 s na API")
    if avatares:
        # aviso de IA fixo durante o vídeo inteiro, dentro da área segura
        blocos.append(f'<div id="selo-ia" class="clip selo-ia" data-start="0" data-duration="{duracao}" '
                      f'data-track-index="9">Avatar digital criado com IA · uso autorizado</div>')

    tip = kit["tipografia"]
    caixa = {"maiusculas": "uppercase", "minusculas": "lowercase"}.get(tip["titulo"].get("caixa"), "none")
    alinhamento = "center" if kit["composicao"].get("alinhamento") == "centro" else "left"
    s = SEGURO
    doc = f"""<!doctype html>
<html lang="pt-BR" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={LARGURA}, height={ALTURA}" />
    <!-- gerado por montar_reel.py a partir de {roteiro_path.name} e do brand kit v{kit.get('versao', 1)} -->
    <script src="assets/gsap.min.js"></script>
    <style>
{css_fontes}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {LARGURA}px; height: {ALTURA}px; overflow: hidden; background: {cores['fundo']}; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden;
        font-family: '{tip['texto']['familia']}', sans-serif; font-weight: {tip['texto'].get('peso', 400)}; }}
      .cena {{ position: absolute; inset: 0; overflow: hidden; }}
      .solido {{ background: {cores['fundo']}; color: {cores['texto']}; }}
      .sobre-midia, .sobre-video {{ color: {cores.get('texto_sobre_foto', '#ffffff')}; }}
      .midia, .midia-video {{ position: absolute; inset: 0; overflow: hidden; }}
      .midia img, .midia-video video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
      .veu {{ position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,.10) 0%, rgba(0,0,0,.28) 35%,
        rgba(0,0,0,.80) 62%, rgba(0,0,0,.85) 100%); }}
      .sobre-midia .titulo, .sobre-video .titulo {{ text-shadow: 0 2px 24px rgba(0,0,0,.45); }}
      .texto-area {{ position: absolute; top: {s['topo']}px; bottom: {s['base']}px; left: {s['esquerda']}px; right: {s['direita']}px;
        display: flex; flex-direction: column; justify-content: flex-end; gap: 28px; text-align: {alinhamento};
        align-items: {'center' if alinhamento == 'center' else 'flex-start'}; }}
      .solido .texto-area {{ justify-content: center; }}
      .titulo {{ font-family: '{tip['titulo']['familia']}', serif; font-weight: {tip['titulo'].get('peso', 700)};
        text-transform: {caixa}; font-size: 96px; line-height: 1.05; letter-spacing: -0.01em; }}
      .titulo.grande {{ font-size: 120px; }}
      .titulo span {{ display: inline-block; }}
      .rotulo {{ font-size: 34px; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; color: {cores['primaria']}; }}
      .sobre-midia .rotulo, .sobre-video .rotulo {{ color: inherit; }}
      .subtitulo {{ font-size: 44px; line-height: 1.3; }}
      .logo-cta {{ height: 120px; width: auto; }}
      .fundo-marca {{ background: {cores['primaria']}; }}
      .midia-avatar {{ position: absolute; inset: 0; }}
      .midia-avatar video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
      .avatar-base {{ top: 30%; }}
      .avatar-base video {{ object-fit: contain; object-position: center bottom; }}
      /* texto sobre avatar vai em caixa com o par fundo/texto do kit: contraste garantido
         sem escurecer a pessoa */
      .cena-avatar .titulo, .cena-avatar .rotulo {{ background: {cores['fundo']}; color: {cores['texto']};
        padding: 14px 24px; border-radius: 18px; }}
      .cena-avatar .titulo {{ font-size: 80px; }}
      .selo-ia {{ position: absolute; top: 150px; left: {s['esquerda']}px; padding: 10px 18px; border-radius: 999px;
        background: rgba(0,0,0,.55); color: #fff; font-size: 26px; font-weight: 600; letter-spacing: .01em; }}
      .assinatura {{ font-size: 40px; font-weight: 600; color: {cores['primaria']}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duracao}" data-width="{LARGURA}" data-height="{ALTURA}">
      {chr(10).join('      ' + b for b in blocos).strip()}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join('      ' + tw for tw in tweens).strip()}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""
    shutil.rmtree(projeto / "assets", ignore_errors=True)
    assets.rename(projeto / "assets")
    (projeto / "index.html").write_text(doc, encoding="utf-8")
    (projeto / "package.json").write_text(json.dumps({
        "name": re.sub(r"[^a-z0-9-]", "-", base.name.lower()), "private": True, "type": "module",
        "scripts": {k: f"npx --yes hyperframes@{HYPERFRAMES_VERSAO} {v}" for k, v in
                    {"dev": "preview", "check": "check", "render": "render -o reel-mudo.mp4"}.items()},
    }, indent=2), encoding="utf-8")
    (projeto / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"assets": "assets"}, "media": {"autoProxy": True},
    }, indent=2), encoding="utf-8")

    deixas = propor_deixas(video_kit.get("sfx_familia", "sutil"), roteiro.get("trilha"), textos, cortes, cenas, duracao)
    deixas["manter_audio_original"] = som_original
    arq_av = projeto / "avatares.json"
    if avatares:
        arq_av.write_text(json.dumps({"avatares": sorted(set(avatares))}, ensure_ascii=False), encoding="utf-8")
    elif arq_av.exists():
        arq_av.unlink()
    arq_deixas = projeto / "deixas.json"
    arq_deixas.write_text(json.dumps(deixas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"projeto: {projeto}")
    print(f"  {len(cenas)} cenas · {duracao}s · estilo {'enérgico' if energico else 'sóbrio'} · legenda {legenda}")
    print(f"  deixas propostas: {len(deixas['deixas'])} efeito(s) em {arq_deixas.name} — revise antes de mixar")


def propor_deixas(familia, trilha, textos, cortes, cenas, duracao):
    """Ponto de partida, não decisão: um efeito por evento visual, respeitando
    a família do kit e o espaçamento mínimo de 1,5 s entre efeitos. Gancho e CTA
    têm prioridade sobre cortes — num conflito, sai o efeito do corte."""
    deixas = []
    if familia != "nenhum":
        forte = familia == "impacto"
        eventos = []  # (prioridade, t, sfx, ganho, nota)
        if textos:
            eventos.append((0, max(0.0, textos[0] - 0.08), "hit-seco" if forte else "pop", -8, "gancho: primeiro texto"))
        if cenas[-1]["tipo"] == "cta":
            inicio_cta = sum(float(c["duracao"]) for c in cenas[:-1])
            eventos.append((0, inicio_cta + 0.52, "impacto-grave" if forte else "ding", -8, "CTA / assinatura"))
        for c in cortes:
            eventos.append((1, max(0.0, c - 0.08), "whoosh-curto" if forte else "swipe", -12, "corte de cena"))
        for _, tt, sfx, g, nota in sorted(eventos):
            if tt < duracao - 0.2 and all(abs(tt - d["t"]) >= 1.5 for d in deixas):
                deixas.append({"t": round(tt, 3), "sfx": sfx, "ganho_db": g, "nota": nota})
        deixas.sort(key=lambda d: d["t"])
    return {
        "trilha": {"id": trilha, "ganho_db": -4, "fade_out_s": 1.2} if trilha else None,
        "manter_audio_original": False,
        "ducking": True,
        "deixas": deixas,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roteiro", type=Path)
    montar(ap.parse_args().roteiro)


if __name__ == "__main__":
    main()
