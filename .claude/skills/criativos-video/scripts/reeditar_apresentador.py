#!/usr/bin/env python3
"""Reedição de vídeo com apresentador — o ESTILO PADRÃO do estúdio para vídeos em
que uma pessoa do cliente fala para a câmera. Monta um projeto HyperFrames
(1080x1920) com o vídeo original em tela cheia e, por cima, motion na identidade do
brand kit: legenda sincronizada à fala (numa tarja que também cobre legenda antiga
queimada no vídeo), manchete de gancho legível no quadro 0, ícones vetoriais
originais que ilustram o que é dito, punch-ins, cartela de tela cheia (a voz segue
por baixo), logo e cartela final de contato pelo WhatsApp do kit.

Uso:
    python reeditar_apresentador.py clientes/<handle>/criativos/<id>/roteiro-reedicao.json
    # depois, em <id>/video/:
    npx --yes hyperframes@<versão> check
    npx --yes hyperframes@<versão> render -o reel-mudo.mp4
    python .claude/skills/efeitos-sonoros/scripts/mixar_sfx.py reel-mudo.mp4 deixas.json --saida reel.mp4
    python .claude/skills/criativos-video/scripts/validar_reel.py reel.mp4

roteiro-reedicao.json (tempos em segundos do vídeo ORIGINAL; formato completo em
references/reedicao-apresentador.md):
    {
      "brand_kit": "../../brand-kit.json",
      "video": "../../referencias/cliente/videos/x.mp4",     # só vídeo do próprio cliente
      "corte": [0, 18.5],                                     # trecho usado (início, fim)
      "trilha": "pulso-leve-100bpm", "ganho_trilha": -12,     # sob a voz, com ducking
      "origem_zoom_y": 67,                                    # % da altura onde o punch-in ancora
      "cobrir_legenda_antiga": {"topo": 1218},                # tarja sobre a legenda queimada (opcional)
      "zooms":    [{"t": 3.5, "s": 1.08}],
      "legendas": [[0.3, 1.3, "Texto da *fala*"]],            # *ênfase* na cor de destaque
      "graficos": [
        {"tipo": "manchete", "t": 0, "ate": 4.6, "texto": "Gancho *escrito*"},
        {"tipo": "tile", "icone": "relogio", "icone_texto": "24h", "x": 72, "y": 560, "t": 9.5, "ate": 13, "rotulo": "..."},
        {"tipo": "risco", "t": 3.55, "ate": 4.6, "topo": 418, "largura": 690},
        {"tipo": "cartela", "t": 14.9, "ate": 16.7, "rotulo": "...", "texto": "...", "icones": [["loja", "..."]]},
        {"tipo": "logo", "t": 16.7, "ate": 18.5}
      ],
      "cta": {"rotulo": "...", "titulo": "Chama no *WhatsApp.*", "botao_sub": "...", "ilustracao": "../../material-cliente/x.png"}
    }

Regras que o script impõe:
    - brand kit validado; vídeo e ilustrações dentro da pasta do cliente, fora de pastas de terceiros
    - ícones só da biblioteca original deste script (nenhum logotipo de terceiros)
    - efeitos sonoros do catálogo e da família do kit (video.sfx_familia)
    - nenhuma contagem na tela (01/06, 3/5...): regra do estúdio
    - o WhatsApp da cartela final vem de contato.whatsapp do kit (nada digitado à mão)
"""

import argparse
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SKILLS = AQUI.parents[1]


def _mod(p, n):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


MR = _mod(AQUI / "montar_reel.py", "montar_reel")
W, H = MR.LARGURA, MR.ALTURA
SEG = MR.SEGURO
CONTAGEM = re.compile(r"\b\d{1,2}\s*/\s*\d{1,2}\b")


# ------------------------------------------------------------------ ícones originais
# Objetos arredondados em 2D: traço na cor "tinta" (a mais escura do par fundo/texto),
# preenchimento "papel" (claro), acentos primária/secundária. Nenhum é marca de terceiros.
_S = 'stroke="var(--tinta)" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"'


def icone(nome, texto=""):
    t = html.escape(texto)
    grade = lambda xs, ys, x0, y0, dx, dy, w, h, f: "".join(  # noqa: E731
        f'<rect x="{x0 + x * dx}" y="{y0 + y * dy}" width="{w}" height="{h}" rx="3" fill="{f(x, y)}"/>'
        for x in range(xs) for y in range(ys))
    I = {
        "loja": f'''<path d="M40 88h120v82H40z" fill="var(--papel)" {_S}/><path d="M30 88l14-34h112l14 34z" fill="var(--pri)" {_S}/>
<path d="M58 54l-6 34M86 54l-4 34M114 54l4 34M142 54l6 34" {_S} fill="none"/><rect x="52" y="104" width="34" height="28" rx="4" fill="var(--sec)" {_S}/>
<rect x="104" y="112" width="34" height="58" rx="4" fill="var(--tinta)" {_S}/><path d="M22 170h156" {_S}/>''',
        "predio-medio": f'''<rect x="44" y="58" width="112" height="112" rx="10" fill="var(--papel)" {_S}/><path d="M44 80h112" {_S}/>
{grade(3, 3, 62, 94, 30, 24, 18, 14, lambda x, y: "var(--sec)" if (x + y) % 2 else "var(--tinta)")}
<rect x="88" y="150" width="24" height="20" fill="var(--pri)" {_S}/><path d="M22 170h156" {_S}/>''',
        "predio-grande": f'''<rect x="64" y="22" width="72" height="148" rx="8" fill="var(--papel)" {_S}/><path d="M100 22V6" {_S}/><circle cx="100" cy="6" r="5" fill="var(--pri)"/>
<path d="M64 42h72" {_S}/>{grade(3, 5, 76, 54, 18, 20, 12, 12, lambda x, y: "var(--sec)" if (x * 3 + y) % 3 else "var(--tinta)")}
<rect x="88" y="152" width="24" height="18" fill="var(--pri)" {_S}/><path d="M22 170h156" {_S}/>''',
        "torre": f'''<path d="M60 170V40l40-22 40 22v130z" fill="var(--sec)" {_S}/>{"".join(f'<path d="M72 {60 + i * 20}h56" stroke="var(--papel)" stroke-width="5"/>' for i in range(5))}<path d="M22 170h156" {_S}/>''',
        "tesoura": f'''<path d="M72 80L168 132" stroke="var(--tinta)" stroke-width="16" stroke-linecap="round"/><path d="M72 120L168 68" stroke="var(--pri)" stroke-width="16" stroke-linecap="round"/>
<circle cx="52" cy="70" r="22" fill="var(--papel)" {_S}/><circle cx="52" cy="130" r="22" fill="var(--papel)" {_S}/><circle cx="112" cy="100" r="7" fill="var(--papel)" {_S}/>''',
        "secador": f'''<rect x="40" y="56" width="104" height="62" rx="31" fill="var(--pri)" {_S}/><rect x="136" y="68" width="30" height="38" rx="6" fill="var(--papel)" {_S}/>
<rect x="66" y="108" width="30" height="66" rx="12" fill="var(--tinta)" {_S}/><circle cx="72" cy="87" r="13" fill="var(--papel)" {_S}/>
<path d="M178 74h14M180 88h16M178 102h14" stroke="var(--sec)" stroke-width="7" stroke-linecap="round"/>''',
        "chave": f'''<g transform="rotate(-40 100 100)"><rect x="86" y="70" width="28" height="112" rx="14" fill="var(--pri)" {_S}/>
<path d="M100 12a38 38 0 1 0 0.1 0z" fill="var(--papel)" {_S}/><path d="M86 8h28v36H86z" fill="var(--papel)"/><path d="M86 12v30h28V12" fill="none" {_S}/></g>''',
        "chat-ia": f'''<path d="M30 46h120a16 16 0 0 1 16 16v58a16 16 0 0 1-16 16H84l-30 26v-26H30a16 16 0 0 1-16-16V62a16 16 0 0 1 16-16z" fill="var(--sec)" {_S}/>
<circle cx="60" cy="91" r="8" fill="var(--papel)"/><circle cx="90" cy="91" r="8" fill="var(--papel)"/><circle cx="120" cy="91" r="8" fill="var(--papel)"/>
<path d="M170 10l7 19 19 7-19 7-7 19-7-19-19-7 19-7z" fill="var(--pri)" {_S}/>''',
        "chip": f'''<rect x="50" y="50" width="100" height="100" rx="18" fill="var(--tinta)" {_S}/><rect x="70" y="70" width="60" height="60" rx="10" fill="var(--sec)"/>
{"".join(f'<path d="M{70 + i * 20} 50V30M{70 + i * 20} 150v20M50 {70 + i * 20}H30M150 {70 + i * 20}h20" {_S}/>' for i in range(4))}
<text x="100" y="112" text-anchor="middle" font-family="var(--ft)" font-weight="900" font-size="34" fill="var(--papel)">{t or "IA"}</text>''',
        "faisca": f'''<path d="M100 20l18 52 52 18-52 18-18 52-18-52-52-18 52-18z" fill="var(--pri)" {_S}/><path d="M160 130l6 16 16 6-16 6-6 16-6-16-16-6 16-6z" fill="var(--sec)" {_S}/>''',
        "relogio": f'''<circle cx="100" cy="100" r="78" fill="var(--papel)" {_S}/><circle class="arco" cx="100" cy="100" r="62" fill="none" stroke="var(--pri)" stroke-width="14"
stroke-linecap="round" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100" transform="rotate(-90 100 100)"/>
{f'<text x="100" y="116" text-anchor="middle" font-family="var(--ft)" font-weight="900" font-size="46" fill="var(--tinta)">{t}</text>' if t else '<path d="M100 100V58M100 100l28 18" ' + _S + '/>'}''',
        "check": f'''<path d="M34 40h132a14 14 0 0 1 14 14v70a14 14 0 0 1-14 14H90l-32 26v-26H34a14 14 0 0 1-14-14V54a14 14 0 0 1 14-14z" fill="var(--papel)" {_S}/>
<path class="traco" d="M66 90l24 24 46-48" fill="none" stroke="var(--pri)" stroke-width="14" stroke-linecap="round" stroke-linejoin="round" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/>''',
        "calendario": f'''<rect x="30" y="44" width="140" height="126" rx="16" fill="var(--papel)" {_S}/><path d="M30 80h140" {_S}/><path d="M64 30v28M136 30v28" {_S}/>
{grade(4, 2, 50, 98, 28, 30, 18, 18, lambda x, y: "var(--pri)" if (x, y) == (2, 0) else "var(--sec)")}''',
        "sino": f'''<path d="M100 30c-30 0-46 22-46 52v34l-16 20h124l-16-20V82c0-30-16-52-46-52z" fill="var(--pri)" {_S}/><circle cx="100" cy="152" r="14" fill="var(--papel)" {_S}/>
<path d="M156 40a60 60 0 0 1 18 30M44 40a60 60 0 0 0-18 30" stroke="var(--sec)" stroke-width="7" fill="none" stroke-linecap="round"/>''',
        "lua": f'''<path d="M130 30a70 70 0 1 0 40 110A58 58 0 0 1 130 30z" fill="var(--papel)" {_S}/><path d="M60 40l5 13 13 5-13 5-5 13-5-13-13-5 13-5z" fill="var(--pri)"/>''',
        "pessoa": f'''<circle cx="100" cy="70" r="32" fill="var(--papel)" {_S}/><path d="M40 170c0-36 26-58 60-58s60 22 60 58z" fill="var(--sec)" {_S}/>''',
        "balanca": f'''<path d="M100 30v130M60 160h80" {_S}/><path d="M36 58h128" {_S}/><circle cx="100" cy="42" r="10" fill="var(--pri)" {_S}/>
<path d="M36 58l-22 52h44zM164 58l-22 52h44z" fill="none" {_S}/><path d="M12 110a24 14 0 0 0 48 0zM140 110a24 14 0 0 0 48 0z" fill="var(--sec)" {_S}/>''',
        "seta-cresce": f'''<path d="M30 160l50-50 30 30 60-70" fill="none" stroke="var(--pri)" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M136 64h40v40" fill="none" stroke="var(--pri)" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>''',
    }
    if nome not in I:
        sys.exit(f"ícone '{nome}' não existe na biblioteca ({', '.join(sorted(I))}) — "
                 "desenhe um novo aqui, genérico e original; logotipo de terceiros nunca")
    return f'<svg viewBox="0 0 200 200" class="ico ico-{nome}">{I[nome]}</svg>'


ICONES = ("loja", "predio-medio", "predio-grande", "torre", "tesoura", "secador", "chave", "chat-ia", "chip",
          "faisca", "relogio", "check", "calendario", "sino", "lua", "pessoa", "seta-cresce", "balanca")


# ------------------------------------------------------------------ utilidades

def palavras(txt, cls):
    """quebra em palavras preservando *ênfase*; cada palavra vira um span animável"""
    out, dentro = [], False
    for tok in re.split(r"(\*)", txt):
        if tok == "*":
            dentro = not dentro
            continue
        for w in tok.split():
            w = html.escape(w)
            out.append(f'<span class="{cls}">{"<em>" + w + "</em>" if dentro else w}</span>')
    return " ".join(out)


def em(txt):
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", html.escape(txt))


def luminancia(hexa):
    r, g, b = (int(hexa.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


class Reedicao:
    def __init__(self, roteiro_path: Path):
        self.rp = roteiro_path
        self.r = json.loads(roteiro_path.read_text(encoding="utf-8"))
        self.base = roteiro_path.parent.resolve()
        self.kit_path = (self.base / self.r["brand_kit"]).resolve()
        v = subprocess.run([sys.executable, str(MR.render_img.VALIDADOR), "--validar", str(self.kit_path)],
                           capture_output=True, text=True)
        if v.returncode:
            sys.exit("brand kit não validado — nenhum criativo antes disso:\n" + v.stdout)
        self.kit = json.loads(self.kit_path.read_text(encoding="utf-8"))
        self.cli = self.kit_path.parent
        self.proj = self.base / "video"
        self.tmp = self.proj / "assets.montando"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir(parents=True)
        shutil.copy2(MR.gsap_local(), self.tmp / "gsap.min.js")
        self.css_fontes = MR.fontes_locais(self.kit, self.tmp / "fontes", self.cli)
        tip = self.kit["tipografia"]
        rot = tip.get("rotulo") or {}
        if rot.get("familia") and rot.get("google_fonts", True) and (rot["familia"], rot.get("peso")) not in {
                (tip[p]["familia"], tip[p].get("peso")) for p in ("titulo", "texto")}:
            bloco = MR.render_img.google_font_local(rot["familia"], rot.get("peso", 700))
            for url in re.findall(r"url\((file://[^)]+)\)", bloco):
                origem = Path(re.sub(r"^file://", "", url).replace("%20", " "))
                nome = f"rotulo-{origem.parent.parent.name}-{origem.name}"
                shutil.copy2(origem, self.tmp / "fontes" / nome)
                bloco = bloco.replace(url, f"assets/fontes/{nome}")
            self.css_fontes += "\n" + bloco
        self.n = 0
        self.el, self.tw, self.deixas = [], [], []
        el = self.kit.get("elementos", {})
        logo = (el.get("logo_variantes") or {}).get("sobre_escuro") or el.get("logo")
        self.logo = self.midia(logo, do_kit=True) if logo else None
        self.catalogo = {i["id"]: i for i in json.loads(
            (SKILLS / "efeitos-sonoros/biblioteca/catalogo.json").read_text(encoding="utf-8"))["itens"]}
        self.familia = self.kit.get("video", {}).get("sfx_familia", "sutil")

    def midia(self, rel, do_kit=False):
        p = ((self.cli if do_kit else self.base) / rel).resolve()
        if not p.exists():
            sys.exit(f"mídia não encontrada: {p}")
        if self.cli not in p.parents:
            sys.exit(f"mídia fora da pasta do cliente ({self.cli}): {p}\nReel só usa material do próprio cliente.")
        if any(t in str(p.relative_to(self.cli)).lower() for t in MR.PROIBIDO):
            sys.exit(f"mídia em pasta de referência de terceiros: {p}")
        self.n += 1
        d = self.tmp / f"m{self.n:02d}{p.suffix.lower()}"
        shutil.copy2(p, d)
        return f"assets/{d.name}"

    def id(self, pre):
        self.n += 1
        return f"{pre}{self.n}"

    def T(self, s):
        self.tw.append(s)

    def sfx(self, t, nome, g=-10, nota=""):
        item = self.catalogo.get(nome)
        if not item or item["tipo"] != "sfx":
            sys.exit(f"efeito '{nome}' não está no catálogo de sons")
        if self.familia == "nenhum" or (self.familia == "sutil" and item["familia"] != "sutil"):
            sys.exit(f"efeito '{nome}' é da família '{item['familia']}' e o kit pede '{self.familia}'")
        self.deixas.append({"t": round(max(0, t - 0.06), 3), "sfx": nome, "ganho_db": g, "nota": nota})

    def sem_contagem(self, texto, onde):
        if CONTAGEM.search(texto or ""):
            sys.exit(f"{onde}: '{texto}' parece contagem (ex.: 01/06) — regra do estúdio: nada de contagem na tela")


def montar(roteiro_path: Path):
    c = Reedicao(roteiro_path)
    r, kit = c.r, c.kit
    ini, fim = map(float, r["corte"])
    fala = round(fim - ini, 3)
    if fala < 1:
        sys.exit("corte com menos de 1 s")
    cta = r.get("cta") or {}
    if not cta.get("titulo"):
        sys.exit("cta.titulo é obrigatório — a reedição sempre termina na cartela de contato")
    contato = (kit.get("contato") or {}).get("whatsapp")
    if not contato:
        sys.exit("contato.whatsapp ausente no brand kit — a cartela final mostra o número do kit, nunca digitado à mão")
    cta_d = float(r.get("cta_duracao", 3.4))
    dur = round(fala + cta_d, 3)
    src = c.midia(r["video"])

    c.el.append(f'<div id="cam" class="camada" style="transform-origin:50% {r.get("origem_zoom_y", 50)}%">'
                f'<video id="v1" src="{src}" data-start="0" data-duration="{fala:.3f}" data-media-start="{ini:.3f}" '
                f'data-track-index="0" muted playsinline style="width:100%;height:100%;object-fit:cover;display:block"></video></div>')
    c.el.append(f'<audio id="voz" src="{src}" data-start="0" data-duration="{fala:.3f}" data-media-start="{ini:.3f}" '
                f'data-track-index="10" data-volume="1"></audio>')
    c.el.append('<div id="vinheta" class="camada vinheta"></div>')

    for z in r.get("zooms", []):
        c.T(f'tl.to("#cam", {{scale:{z["s"]}, duration:{z.get("d", 0.35)}, ease:"{z.get("ease", "power3.out")}"}}, {z["t"] - ini:.3f});')
        if z.get("sfx"):
            c.sfx(z["t"] - ini, z["sfx"], -12, "punch-in")

    cobrir = r.get("cobrir_legenda_antiga")
    topo_tarja = int((cobrir or {}).get("topo", r.get("tarja_topo", 1218)))
    if r.get("legendas"):
        leg = r["legendas"]
        c.el.append('<div id="tarja" class="tarja"></div>')
        # a tarja entra logo antes da primeira fala; com legenda antiga queimada, ela fica
        # até o fim da fala cobrindo aquela faixa (conferir no quadro ampliado)
        t_on = max(0, float((cobrir or {}).get("de", leg[0][0] - 0.05)) - ini)
        c.T(f'tl.fromTo("#tarja", {{opacity:0, scaleX:0.85}}, {{opacity:1, scaleX:1, duration:0.25, ease:"power2.out"}}, {t_on:.3f});')
        c.T(f'tl.to("#tarja", {{opacity:0, duration:0.2}}, {fala - 0.2:.3f});')
        for i, (a, b, txt) in enumerate(leg):
            c.sem_contagem(txt, f"legenda {i + 1}")
            a, b = max(a, ini) - ini, min(b, fim) - ini
            eid = f"leg{i}"
            c.el.append(f'<div id="{eid}" class="leg">{palavras(txt, eid + "-w")}</div>')
            c.T(f'tl.fromTo("#{eid}", {{opacity:0}}, {{opacity:1, duration:0.01}}, {a:.3f});')
            c.T(f'tl.fromTo(".{eid}-w", {{opacity:0, y:22, scale:0.9}}, {{opacity:1, y:0, scale:1, duration:0.22, '
                f'ease:"back.out(2.2)", stagger:0.05}}, {a:.3f});')
            c.T(f'tl.to("#{eid}", {{opacity:0, duration:0.01}}, {b - 0.01:.3f});')

    for g in r.get("graficos", []):
        t0 = float(g["t"]) - ini
        t1 = (float(g["ate"]) - ini) if g.get("ate") is not None else None
        tipo = g["tipo"]
        c.sem_contagem(g.get("texto", "") + " " + g.get("rotulo", ""), f"gráfico {tipo} em {g['t']}s")
        if tipo == "manchete":
            eid = c.id("man")
            c.el.append(f'<div id="{eid}" class="manchete placa" style="top:{g.get("topo", 250)}px;font-size:{g.get("tam", 92)}px">'
                        f'{palavras(g["texto"], eid + "-w")}</div>')
            if t0 <= 0.01:  # gancho: legível no quadro 0, só um "punch" de escala
                c.T(f'tl.fromTo("#{eid}", {{scale:1.08}}, {{scale:1, duration:0.5, ease:"power2.out", transformOrigin:"left top"}}, 0);')
            else:
                c.T(f'tl.fromTo("#{eid}", {{opacity:0}}, {{opacity:1, duration:0.01}}, {t0:.3f});')
                c.T(f'tl.fromTo(".{eid}-w", {{opacity:0, y:50, rotation:4}}, {{opacity:1, y:0, rotation:0, duration:0.42, '
                    f'ease:"back.out(1.8)", stagger:0.06}}, {t0:.3f});')
            if t1 is not None:
                c.T(f'tl.to("#{eid}", {{opacity:0, y:-30, duration:0.28, ease:"power2.in"}}, {t1 - 0.28:.3f});')
        elif tipo == "tile":
            eid = c.id("ico")
            tam = g.get("tam", 200)
            lab = f'<div class="tile-rot">{html.escape(g["rotulo"])}</div>' if g.get("rotulo") else ""
            c.el.append(f'<div id="{eid}" class="tile-wrap" style="left:{g["x"]}px;top:{g["y"]}px;width:{tam}px">'
                        f'<div class="tile" style="width:{tam}px;height:{tam}px">{icone(g["icone"], g.get("icone_texto", ""))}</div>{lab}</div>')
            c.T(f'tl.fromTo("#{eid}", {{opacity:0, scale:0.4, rotation:{g.get("gira", -10)}}}, {{opacity:1, scale:1, rotation:0, '
                f'duration:0.5, ease:"back.out(2)"}}, {t0:.3f});')
            vida = ((t1 if t1 is not None else t0 + 2) - t0 - 0.6) / 2
            c.T(f'tl.fromTo("#{eid} .tile", {{y:0}}, {{y:-10, duration:{max(0.3, vida):.2f}, ease:"sine.inOut", yoyo:true, repeat:1}}, {t0 + 0.5:.3f});')
            if g["icone"] == "relogio":
                c.T(f'tl.to("#{eid} .arco", {{strokeDashoffset:0, duration:1.1, ease:"power2.inOut"}}, {t0 + 0.3:.3f});')
            if g["icone"] == "check":
                c.T(f'tl.to("#{eid} .traco", {{strokeDashoffset:0, duration:0.5, ease:"power2.out"}}, {t0 + 0.35:.3f});')
            if t1 is not None:
                c.T(f'tl.to("#{eid}", {{opacity:0, scale:0.7, duration:0.25, ease:"power2.in"}}, {t1 - 0.25:.3f});')
        elif tipo == "risco":
            eid = c.id("rsc")
            c.el.append(f'<div id="{eid}" class="risco" style="top:{g["topo"]}px;width:{g.get("largura", 700)}px"></div>')
            c.T(f'tl.fromTo("#{eid}", {{scaleX:0}}, {{scaleX:1, duration:0.3, ease:"power3.out"}}, {t0:.3f});')
            if t1 is not None:
                c.T(f'tl.to("#{eid}", {{opacity:0, duration:0.25}}, {t1 - 0.25:.3f});')
        elif tipo == "selo":
            eid = c.id("sel")
            c.el.append(f'<div id="{eid}" class="selo" style="top:{g.get("topo", 250)}px">{em(g["texto"])}</div>')
            c.T(f'tl.fromTo("#{eid}", {{opacity:0, scale:1.6, rotation:-6}}, {{opacity:1, scale:1, rotation:-3, duration:0.4, ease:"back.out(2.5)"}}, {t0:.3f});')
            if t1 is not None:
                c.T(f'tl.to("#{eid}", {{opacity:0, y:-20, duration:0.25}}, {t1 - 0.25:.3f});')
        elif tipo == "cartela":
            # corte para tela cheia na cor de fundo da marca; a voz continua por baixo
            eid = c.id("crt")
            itens = "".join(f'<div class="ct-item" id="{eid}-i{j}"><div class="tile" style="width:230px;height:230px">{icone(ic)}</div>'
                            f'<div class="tile-rot">{html.escape(rt)}</div></div>' for j, (ic, rt) in enumerate(g.get("icones", [])))
            c.el.append(f'<div id="{eid}" class="cartela"><div class="rotulo"><i></i>{html.escape(g.get("rotulo", ""))}</div>'
                        f'<h2 class="ct-tit">{palavras(g["texto"], eid + "-w")}</h2><div class="ct-fila">{itens}</div></div>')
            c.T(f'tl.fromTo("#{eid}", {{clipPath:"circle(0% at 50% 50%)", opacity:0}}, {{clipPath:"circle(75% at 50% 50%)", opacity:1, '
                f'duration:0.4, ease:"power3.inOut"}}, {t0:.3f});')
            c.T(f'tl.fromTo(".{eid}-w", {{opacity:0, y:60}}, {{opacity:1, y:0, duration:0.4, ease:"back.out(1.8)", stagger:0.06}}, {t0 + 0.15:.3f});')
            for j in range(len(g.get("icones", []))):
                c.T(f'tl.fromTo("#{eid}-i{j}", {{opacity:0, y:120, scale:0.5}}, {{opacity:1, y:0, scale:1, duration:0.45, '
                    f'ease:"back.out(2)"}}, {t0 + 0.2 + j * 0.12:.3f});')
            c.T(f'tl.to("#{eid}", {{clipPath:"circle(0% at 50% 50%)", duration:0.3, ease:"power3.in"}}, {t1 - 0.3:.3f});')
            c.T(f'tl.set("#{eid}", {{opacity:0}}, {t1:.3f});')
        elif tipo == "logo":
            eid = c.id("mrc")
            if c.logo:
                c.el.append(f'<img id="{eid}" class="logo-topo" src="{c.logo}" alt="" style="top:{g.get("topo", 260)}px">')
            else:
                c.el.append(f'<div id="{eid}" class="logo-topo assin" style="top:{g.get("topo", 260)}px">'
                            f'{html.escape(kit["elementos"].get("assinatura", ""))}</div>')
            c.T(f'tl.fromTo("#{eid}", {{opacity:0, x:-30}}, {{opacity:1, x:0, duration:0.45, ease:"power3.out"}}, {t0:.3f});')
            if t1 is not None:
                c.T(f'tl.to("#{eid}", {{opacity:0, y:-20, duration:0.3, ease:"power2.in"}}, {t1 - 0.3:.3f});')
        else:
            sys.exit(f"gráfico '{tipo}' inválido (manchete, tile, risco, selo, cartela, logo)")
        if g.get("sfx"):
            c.sfx(t0, g["sfx"], g.get("ganho", -10), f"{tipo} {g.get('icone', '')}".strip())

    # cartela final de contato
    c.sem_contagem(cta.get("titulo", "") + " " + cta.get("rotulo", ""), "cta")
    t0 = fala
    ilu = f'<img id="cta-ilu" class="cta-ilu" src="{c.midia(cta["ilustracao"])}" alt="">' if cta.get("ilustracao") else ""
    logo_cta = (f'<img id="cta-logo" class="cta-logo" src="{c.logo}" alt="">' if c.logo else
                f'<div id="cta-logo" class="cta-logo assin">{html.escape(kit["elementos"].get("assinatura", ""))}</div>')
    sub = cta.get("sub") or kit["elementos"].get("assinatura", "")
    c.el.append(f'''<section id="cta" class="clip cta" data-start="{t0:.3f}" data-duration="{cta_d:.3f}" data-track-index="3">
<div class="cta-in">{logo_cta}
<div id="cta-rot" class="rotulo"><i></i>{html.escape(cta.get("rotulo", ""))}</div>
<h2 id="cta-h">{palavras(cta["titulo"], "cta-w")}</h2>
<div id="cta-b" class="botao"><span class="bi"><svg viewBox="0 0 24 24" width="50" height="50" fill="none" stroke="var(--papel)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5h16v10H10l-4.5 3.5v-3.5H4z"/><circle cx="9" cy="10.5" r=".7" fill="var(--papel)"/><circle cx="12" cy="10.5" r=".7" fill="var(--papel)"/><circle cx="15" cy="10.5" r=".7" fill="var(--papel)"/></svg></span>
<span><b>{html.escape(contato)}</b>{f"<small>{html.escape(cta['botao_sub'])}</small>" if cta.get("botao_sub") else ""}</span></div>
<p id="cta-sub" class="sub">{em(sub)}</p></div>{ilu}</section>''')
    c.T(f'tl.fromTo("#cta-logo", {{opacity:0, y:-20}}, {{opacity:1, y:0, duration:0.4}}, {t0 + 0.1:.3f});')
    c.T(f'tl.fromTo("#cta-rot", {{opacity:0, x:-30}}, {{opacity:1, x:0, duration:0.4}}, {t0 + 0.2:.3f});')
    c.T(f'tl.fromTo(".cta-w", {{opacity:0, y:60}}, {{opacity:1, y:0, duration:0.45, ease:"back.out(1.8)", stagger:0.07}}, {t0 + 0.25:.3f});')
    c.T(f'tl.fromTo("#cta-b", {{opacity:0, scale:0.6}}, {{opacity:1, scale:1, duration:0.5, ease:"back.out(2.4)"}}, {t0 + 0.7:.3f});')
    c.T(f'tl.to("#cta-b", {{scale:1.04, duration:0.35, ease:"sine.inOut", yoyo:true, repeat:3}}, {t0 + 1.3:.3f});')
    c.T(f'tl.fromTo("#cta-sub", {{opacity:0}}, {{opacity:1, duration:0.4}}, {t0 + 1.0:.3f});')
    if ilu:
        c.T(f'tl.fromTo("#cta-ilu", {{opacity:0, scale:0.5, rotation:12}}, {{opacity:1, scale:1, rotation:0, duration:0.6, ease:"back.out(1.8)"}}, {t0 + 0.5:.3f});')
    if c.familia != "nenhum":
        c.sfx(t0 + 0.02, "swipe" if c.familia == "sutil" else "whoosh-curto", -10, "entra a cartela de contato")
        c.sfx(t0 + 0.7, "ding" if c.familia == "sutil" else "impacto-grave", -8, "botão de contato")

    # cores: tudo do kit
    p = kit["cores"]["papeis"]
    leg = kit.get("video", {}).get("legenda_cores") or {}
    fundo, texto = p["fundo"], p["texto"]
    tinta, papel = sorted([fundo, texto], key=luminancia)
    papel = p.get("claro", papel) if luminancia(p.get("claro", papel)) > 0.5 else papel
    tip = kit["tipografia"]
    rot = tip.get("rotulo") or {}
    s = SEG
    css = f"""
{c.css_fontes}
:root {{ --fundo:{fundo}; --texto:{texto}; --pri:{p['primaria']}; --sec:{p.get('secundaria', p['primaria'])};
  --dest:{p.get('destaque', p['primaria'])}; --sobre-dest:{p.get('texto_sobre_destaque', fundo)};
  --tinta:{tinta}; --papel:{papel}; --leg-caixa:{leg.get('caixa', fundo)}; --leg-texto:{leg.get('texto', texto)};
  --leg-enfase:{leg.get('enfase', p['primaria'])}; --ft:'{tip['titulo']['familia']}'; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:var(--fundo); }}
#root {{ position:relative; width:100%; height:100%; overflow:hidden; font-family:'{tip['texto']['familia']}', sans-serif; color:var(--texto); }}
em {{ font-style:normal; color:var(--pri); }}
.camada {{ position:absolute; inset:0; overflow:hidden; }}
.vinheta {{ background:linear-gradient(180deg, color-mix(in srgb, {tinta} 55%, transparent) 0%, transparent 26%, transparent 60%,
  color-mix(in srgb, {tinta} 45%, transparent) 100%); }}
.manchete {{ position:absolute; left:{s['esquerda']}px; font-family:var(--ft); font-weight:{tip['titulo'].get('peso', 700)};
  line-height:1.0; letter-spacing:-0.02em; color:var(--texto); }}
.manchete span {{ display:inline-block; }}
.placa {{ background:var(--fundo); padding:26px 34px 30px; border-radius:28px; box-shadow:0 18px 50px rgba(0,0,0,.28);
  max-width:{W - s['esquerda'] - s['direita']}px; }}
.rotulo {{ font-family:'{rot.get('familia', tip['texto']['familia'])}'; font-weight:{rot.get('peso', 700)}; font-size:30px;
  letter-spacing:.16em; text-transform:uppercase; color:var(--pri); display:flex; align-items:center; gap:18px; }}
.rotulo i {{ display:block; width:46px; height:4px; background:currentColor; }}
.tile-wrap {{ position:absolute; display:flex; flex-direction:column; align-items:center; gap:14px; }}
.tile {{ background:var(--papel); border-radius:48px; box-shadow:0 22px 44px rgba(0,0,0,.30), inset 0 -8px 0 rgba(0,0,0,.06);
  display:flex; align-items:center; justify-content:center; }}
.tile svg {{ width:78%; height:78%; overflow:visible; }}
.tile-rot {{ background:var(--tinta); color:var(--papel); font-family:var(--ft); font-weight:{tip['titulo'].get('peso', 700)}; font-size:28px;
  padding:10px 18px; border-radius:999px; white-space:nowrap; }}
.tarja {{ position:absolute; left:50%; top:{topo_tarja}px; width:720px; height:150px; margin-left:-360px; background:var(--leg-caixa);
  border-radius:30px; box-shadow:0 16px 40px rgba(0,0,0,.35); }}
.tarja::before {{ content:""; position:absolute; left:0; top:22px; bottom:22px; width:8px; border-radius:0 6px 6px 0; background:var(--pri); }}
.leg {{ position:absolute; left:50%; top:{topo_tarja}px; width:680px; height:150px; margin-left:-340px; display:flex; align-items:center;
  justify-content:center; text-align:center; gap:0 14px; flex-wrap:wrap; font-family:var(--ft); font-weight:{tip['titulo'].get('peso', 700)};
  font-size:58px; line-height:1; color:var(--leg-texto); letter-spacing:-0.01em; }}
.leg em {{ color:var(--leg-enfase); }}
.leg span {{ display:inline-block; }}
.risco {{ position:absolute; left:{s['esquerda'] + 20}px; height:14px; border-radius:8px; background:var(--pri); transform-origin:left center; }}
.selo {{ position:absolute; left:{s['esquerda']}px; background:var(--fundo); color:var(--texto); border-left:14px solid var(--pri);
  font-family:var(--ft); font-weight:{tip['titulo'].get('peso', 700)}; font-size:110px; line-height:1; padding:18px 36px 24px;
  border-radius:30px; box-shadow:0 18px 44px rgba(0,0,0,.3); }}
.logo-topo {{ position:absolute; left:{s['esquerda']}px; height:52px; width:auto; }}
.assin {{ font-family:var(--ft); font-weight:{tip['titulo'].get('peso', 700)}; font-size:40px; color:var(--texto); height:auto; }}
.cartela {{ position:absolute; inset:0; opacity:0; background:var(--fundo); display:flex; flex-direction:column; justify-content:center; gap:40px;
  padding:{s['topo'] + 40}px {s['direita']}px {s['base'] + 170}px {s['esquerda']}px; }}
.ct-tit {{ font-family:var(--ft); font-weight:{tip['titulo'].get('peso', 700)}; font-size:132px; line-height:.95; letter-spacing:-0.03em; color:var(--texto); }}
.ct-tit span {{ display:inline-block; }}
.ct-fila {{ display:flex; gap:26px; align-items:flex-end; }}
.ct-item {{ display:flex; flex-direction:column; align-items:center; gap:16px; }}
.ct-item:nth-child(1) .tile {{ transform:scale(.78); transform-origin:bottom center; }}
.ct-item:nth-child(2) .tile {{ transform:scale(.9); transform-origin:bottom center; }}
.cta {{ position:absolute; inset:0; background:var(--fundo); }}
.cta .cta-in {{ position:absolute; left:{s['esquerda']}px; right:{s['direita']}px; top:300px; bottom:{s['base']}px; display:flex; flex-direction:column; gap:34px; }}
.cta .cta-logo {{ height:56px; width:auto; align-self:flex-start; }}
.cta .rotulo {{ margin-top:30px; }}
.cta h2 {{ font-family:var(--ft); font-weight:{tip['titulo'].get('peso', 700)}; font-size:118px; line-height:.98; letter-spacing:-0.025em; color:var(--texto); }}
.cta h2 span {{ display:inline-block; }}
.cta .botao {{ display:flex; align-items:center; gap:26px; background:var(--dest); color:var(--sobre-dest); border-radius:999px;
  padding:24px 44px 24px 26px; align-self:flex-start; }}
.cta .botao .bi {{ width:86px; height:86px; border-radius:50%; background:var(--sobre-dest); display:flex; align-items:center; justify-content:center; }}
.cta .botao b {{ display:block; font-family:var(--ft); font-weight:{tip['titulo'].get('peso', 700)}; font-size:58px; line-height:1; letter-spacing:-0.01em; }}
.cta .botao small {{ display:block; font-size:30px; font-weight:700; margin-top:6px; letter-spacing:.02em; }}
.cta .sub {{ font-size:34px; line-height:1.35; color:var(--texto); opacity:.8; }}
.cta .cta-ilu {{ position:absolute; right:60px; bottom:{s['base'] - 40}px; width:480px; height:440px; object-fit:contain;
  filter:drop-shadow(0 30px 40px rgba(0,0,0,.35)); }}
"""
    doc = f"""<!doctype html>
<html lang="pt-BR" data-resolution="portrait">
<head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<!-- gerado por reeditar_apresentador.py (estilo padrão de reedição) a partir de {roteiro_path.name} e do brand kit v{kit.get('versao', 1)} -->
<script src="assets/gsap.min.js"></script>
<style>{css}</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="{W}" data-height="{H}">
{chr(10).join(c.el)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(c.tw)}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body></html>"""
    proj = c.proj
    shutil.rmtree(proj / "assets", ignore_errors=True)
    c.tmp.rename(proj / "assets")
    (proj / "index.html").write_text(doc, encoding="utf-8")
    (proj / "package.json").write_text(json.dumps({
        "name": re.sub(r"[^a-z0-9-]", "-", c.base.name.lower()), "private": True, "type": "module",
        "scripts": {k: f"npx --yes hyperframes@{MR.HYPERFRAMES_VERSAO} {v}" for k, v in
                    {"dev": "preview", "check": "check", "render": "render -o reel-mudo.mp4"}.items()}}, indent=2), encoding="utf-8")
    (proj / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"assets": "assets"}, "media": {"autoProxy": True}}, indent=2), encoding="utf-8")
    # no máximo 1 efeito a cada ~1,2 s; o primeiro declarado vence
    ok = []
    for d in sorted(c.deixas, key=lambda d: d["t"]):
        if d["t"] < dur - 0.2 and all(abs(d["t"] - o["t"]) >= 1.2 for o in ok):
            ok.append(d)
    trilha = r.get("trilha")
    (proj / "deixas.json").write_text(json.dumps({
        "trilha": {"id": trilha, "ganho_db": r.get("ganho_trilha", -12), "fade_out_s": 1.2} if trilha else None,
        "manter_audio_original": True, "ducking": True, "deixas": ok}, ensure_ascii=False, indent=2), encoding="utf-8")
    (proj / "avatares.json").unlink(missing_ok=True)
    print(f"projeto: {proj}")
    print(f"  reedição de {fala}s + cartela {cta_d}s = {dur}s · {len(r.get('legendas', []))} legendas · "
          f"{len(r.get('graficos', []))} gráficos · {len(ok)} deixas")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roteiro", type=Path)
    ap.add_argument("--icones", action="store_true", help="lista os ícones da biblioteca e sai")
    a = ap.parse_args()
    if a.icones:
        print("\n".join(ICONES))
        return
    montar(a.roteiro)


if __name__ == "__main__":
    main()
