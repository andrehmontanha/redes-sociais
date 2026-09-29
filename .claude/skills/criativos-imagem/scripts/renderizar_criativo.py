#!/usr/bin/env python3
"""Renderiza criativos estáticos (post, carrossel, story) a partir de um roteiro
JSON e do brand kit do cliente.

Uso:
    python renderizar_criativo.py clientes/<handle>/criativos/<id>/roteiro.json
    python renderizar_criativo.py <roteiro.json> --html-apenas   # só gera o HTML, sem navegador

Roteiro:
    {
      "brand_kit": "../../brand-kit.json",          # relativo ao roteiro
      "formato": "feed",                            # feed 1080x1350 · quadrado 1080x1080 · story 1080x1920
      "pecas": [
        {"template": "capa-carrossel", "campos": {"titulo": "...", "foto": "../../referencias/cliente/x.jpg"}},
        {"template": "lista", "campos": {"titulo": "...", "itens": ["...", "..."]}}
      ]
    }

Saída, ao lado do roteiro:
    render/01-capa-carrossel.jpg ...   JPEG sRGB (o formato que a Graph API aceita)
    render/folha.jpg                    todas as peças lado a lado, para revisão com Read
    render/relatorio.json               avisos de texto estourando a área segura

Regras que o script impõe:
    - brand kit precisa passar na validação (confirmado por humano, sem PENDENTE)
    - toda foto precisa estar dentro da pasta do cliente (a pasta do brand kit):
      material de concorrente ou de tendência nunca vira criativo
    - texto que não cabe na área segura, mesmo depois de reduzir a fonte, é erro
"""

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

AQUI = Path(__file__).resolve().parent
TEMPLATES = AQUI.parent / "templates"
VALIDADOR = AQUI.parents[1] / "identidade-visual" / "scripts" / "extrair_identidade.py"
FORMATOS = {"feed": (1080, 1350), "quadrado": (1080, 1080), "story": (1080, 1920)}
PROIBIDO = ("concorrente", "tendencia", "tendência", "estudo", "referencia/estudo")


# ---------------------------------------------------------------- template

def render_template(texto, dados):
    """Mustache mínimo: {{campo}}, {{{campo_html}}}, {{#secao}}...{{/secao}}, {{^secao}}...{{/secao}}, {{.}}."""
    def secao(m):
        inv, nome, corpo = m.group(1) == "^", m.group(2), m.group(3)
        valor = dados.get(nome)
        if inv:
            return render_template(corpo, dados) if not valor else ""
        if not valor:
            return ""
        if isinstance(valor, list):
            return "".join(render_template(corpo, {**dados, **(v if isinstance(v, dict) else {".": v}), "n": i + 1})
                           for i, v in enumerate(valor))
        return render_template(corpo, dados)

    texto = re.sub(r"{{([#^])(\w+)}}(.*?){{/\2}}", secao, texto, flags=re.S)
    texto = re.sub(r"{{{([\w.]+)}}}", lambda m: str(dados.get(m.group(1), "")), texto)
    return re.sub(r"{{([\w.]+)}}", lambda m: html.escape(str(dados.get(m.group(1), ""))), texto)


def url_arquivo(caminho: Path):
    return "file://" + quote(str(caminho.resolve()))


def resolver_foto(valor, base: Path, raiz_cliente: Path):
    p = (base / valor).resolve()
    if not p.exists():
        sys.exit(f"foto não encontrada: {p}")
    if raiz_cliente not in p.parents:
        sys.exit(f"foto fora da pasta do cliente ({raiz_cliente}): {p}\n"
                 "Criativo só usa material do próprio cliente.")
    if any(t in str(p.relative_to(raiz_cliente)).lower() for t in PROIBIDO):
        sys.exit(f"foto em pasta de referência de terceiros: {p}")
    return url_arquivo(p)


CACHE_FONTES = Path.home() / ".cache" / "estudio-social" / "fontes"
UA_MODERNO = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def google_font_local(familia, peso):
    """Baixa a fonte do Google Fonts uma vez e devolve @font-face apontando para
    o arquivo local. O navegador headless não passa pelo proxy nem confia no CA
    dele; o Python passa. De quebra, o render fica determinístico e offline."""
    import requests
    destino = CACHE_FONTES / re.sub(r"\W+", "-", familia.lower()) / str(peso)
    css_cache = destino / "font.css"
    if not css_cache.exists():
        r = requests.get("https://fonts.googleapis.com/css2",
                         params={"family": f"{familia}:wght@{peso}", "display": "block"},
                         headers={"User-Agent": UA_MODERNO}, timeout=30)
        if r.status_code != 200:
            sys.exit(f"Google Fonts não tem '{familia}' peso {peso} (HTTP {r.status_code}). "
                     "Confira o nome exato em fonts.google.com ou use arquivo do cliente.")
        css = r.text
        destino.mkdir(parents=True, exist_ok=True)
        for i, url in enumerate(dict.fromkeys(re.findall(r"url\((https://[^)]+)\)", css))):
            arq = destino / f"{i}.woff2"
            arq.write_bytes(requests.get(url, timeout=60).content)
            css = css.replace(url, url_arquivo(arq))
        css_cache.write_text(css, encoding="utf-8")
    return css_cache.read_text(encoding="utf-8")


def css_marca(kit, largura, altura, base_kit: Path):
    cores = kit["cores"]["papeis"]
    tip, comp = kit["tipografia"], kit["composicao"]
    faces = []
    for papel in ("titulo", "texto"):
        f = tip[papel]
        if f.get("google_fonts", True):
            faces.append(google_font_local(f["familia"], f.get("peso", 400)))
        elif f.get("arquivo"):
            faces.append(f"@font-face{{font-family:'{f['familia']}';src:url('{url_arquivo(base_kit / f['arquivo'])}');"
                         f"font-weight:{f.get('peso', 400)};}}")
    link = ""
    caixa = {"maiusculas": "uppercase", "minusculas": "lowercase"}.get(tip["titulo"].get("caixa"), "none")
    variaveis = f"""
    :root {{
      --largura: {largura}px; --altura: {altura}px;
      --fundo: {cores['fundo']}; --primaria: {cores['primaria']};
      --destaque: {cores['destaque']}; --texto: {cores['texto']};
      --texto-sobre-foto: {cores.get('texto_sobre_foto', '#ffffff')};
      --fonte-titulo: '{tip['titulo']['familia']}', serif; --peso-titulo: {tip['titulo'].get('peso', 700)};
      --caixa-titulo: {caixa};
      --fonte-texto: '{tip['texto']['familia']}', sans-serif; --peso-texto: {tip['texto'].get('peso', 400)};
      --margem: {comp.get('margem_px', 72)}px; --raio: {comp.get('raio_borda_px', 0)}px;
      --alinhamento: {'center' if comp.get('alinhamento') == 'centro' else 'left'};
    }}"""
    return link, "\n".join(faces) + variaveis


def montar_html(peca, idx, total, kit, formato, base: Path, base_kit: Path):
    largura, altura = FORMATOS[formato]
    arq = TEMPLATES / f"{peca['template']}.html"
    if not arq.exists():
        disponiveis = ", ".join(sorted(p.stem for p in TEMPLATES.glob("*.html")))
        sys.exit(f"template inexistente: {peca['template']} (disponíveis: {disponiveis})")
    campos = dict(peca.get("campos", {}))
    for chave in [k for k in campos if k == "foto" or k.startswith("foto_")]:
        campos[chave] = resolver_foto(campos[chave], base, base_kit)
    elem, comp = kit["elementos"], kit["composicao"]
    if elem.get("logo"):
        campos.setdefault("logo", url_arquivo(base_kit / elem["logo"]))
    assinatura = elem.get("assinatura")
    if assinatura and assinatura != "nenhuma":
        campos.setdefault("assinatura", assinatura)
    campos.update({
        "indice": idx, "total": total, "carrossel": total > 1 and formato != "story",
        "posicao_logo": elem.get("logo_posicao", "topo-esquerda"),
        "classe_alinhamento": "centro" if comp.get("alinhamento") == "centro" else "",
        f"tratamento_{comp.get('texto_sobre_foto', 'degrade')}": True,
        "formato": formato,
    })
    if formato == "story":
        campos["story"] = True
    if peca["template"] == "prova-brand-kit":
        campos["paleta"] = [c["hex"] for c in kit["cores"]["paleta"]]
        campos["papeis"] = [{"nome": k, "hex": v} for k, v in kit["cores"]["papeis"].items()]
        campos.setdefault("fonte_titulo", kit["tipografia"]["titulo"]["familia"])
        campos.setdefault("fonte_texto", kit["tipografia"]["texto"]["familia"])
        campos.setdefault("tratamento", kit["tratamento_foto"].get("leitura", ""))
        campos.setdefault("titulo", "@" + kit["handle"])
    corpo = render_template(arq.read_text(encoding="utf-8"), campos)
    link, variaveis = css_marca(kit, largura, altura, base_kit)
    base_css = (TEMPLATES / "_base.css").read_text(encoding="utf-8")
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">{link}
<style>{variaveis}\n{base_css}</style></head>
<body class="formato-{formato}">{corpo}</body></html>"""


# ---------------------------------------------------------------- render

AJUSTAR_E_CONFERIR = """
async () => {
  await document.fonts.ready;
  // tolerância de 0,22 em: fontes com descendente longo (serifadas display) "vazam"
  // a caixa da linha sem que nenhum texto fique cortado
  const cabe = (el) => {
    const folga = Math.max(2, parseFloat(getComputedStyle(el).fontSize) * 0.22);
    return el.scrollHeight <= el.clientHeight + folga && el.scrollWidth <= el.clientWidth + 1;
  };
  for (const el of document.querySelectorAll('.ajustar')) {
    let tam = parseFloat(getComputedStyle(el).fontSize);
    const min = parseFloat(el.dataset.min || 28);
    while (!cabe(el) && tam > min) { tam -= 2; el.style.fontSize = tam + 'px'; }
  }
  const quadro = document.querySelector('.quadro').getBoundingClientRect();
  const margem = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--margem'));
  const avisos = [];
  for (const el of document.querySelectorAll('.ajustar, .seguro')) {
    const r = el.getBoundingClientRect();
    if (!el.textContent.trim()) continue;
    if (!cabe(el)) avisos.push({erro: true, campo: el.dataset.campo || el.className, msg: 'texto não coube mesmo na fonte mínima'});
    if (r.left < quadro.left + margem - 1 || r.right > quadro.right - margem + 1 ||
        r.top < quadro.top + margem - 1 || r.bottom > quadro.bottom - margem + 1)
      avisos.push({erro: false, campo: el.dataset.campo || el.className, msg: 'invade a margem de segurança'});
  }
  const fontes = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family);
  return {avisos, fontes};
}
"""


def abrir_chromium(p):
    """Usa o Chromium do Playwright; se a versão instalada não bater, cai para
    CHROMIUM_PATH ou para um Chromium já presente na máquina."""
    import glob
    import os
    caminho = os.environ.get("CHROMIUM_PATH")
    if caminho:
        return p.chromium.launch(executable_path=caminho)
    try:
        return p.chromium.launch()
    except Exception as erro:
        base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", str(Path.home() / ".cache/ms-playwright"))
        candidatos = sorted(glob.glob(f"{base}/chromium-*/chrome-linux*/chrome"), reverse=True)
        candidatos += [c for c in ("/usr/bin/chromium", "/usr/bin/google-chrome") if Path(c).exists()]
        if not candidatos:
            raise SystemExit(f"Chromium não encontrado: {erro}\nRode `playwright install chromium` "
                             "ou aponte CHROMIUM_PATH para um Chrome/Chromium.")
        return p.chromium.launch(executable_path=candidatos[0])


def renderizar(htmls, saida: Path, largura, altura):
    from playwright.sync_api import sync_playwright
    from PIL import Image

    saida.mkdir(parents=True, exist_ok=True)
    relatorio, arquivos = [], []
    with sync_playwright() as p:
        nav = abrir_chromium(p)
        pag = nav.new_page(viewport={"width": largura, "height": altura}, device_scale_factor=1)
        for nome, doc in htmls:
            html_path = saida / f"{nome}.html"
            html_path.write_text(doc, encoding="utf-8")
            pag.goto(url_arquivo(html_path), wait_until="networkidle")
            info = pag.evaluate(AJUSTAR_E_CONFERIR)
            png = saida / f"{nome}.png"
            pag.locator(".quadro").screenshot(path=str(png))
            jpg = saida / f"{nome}.jpg"
            Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True, progressive=False)
            png.unlink()
            arquivos.append(jpg)
            relatorio.append({"peca": nome, **info})
        nav.close()
    return arquivos, relatorio


def folha(arquivos, saida: Path, colunas=5, lado=360):
    from PIL import Image
    imgs = [Image.open(a) for a in arquivos]
    esc = lado / imgs[0].width
    w, h = lado, int(imgs[0].height * esc)
    linhas = (len(imgs) + colunas - 1) // colunas
    cols = min(colunas, len(imgs))
    folha = Image.new("RGB", (cols * w + (cols + 1) * 12, linhas * h + (linhas + 1) * 12), "#e5e5e5")
    for i, im in enumerate(imgs):
        x, y = 12 + (i % colunas) * (w + 12), 12 + (i // colunas) * (h + 12)
        folha.paste(im.resize((w, h)), (x, y))
    folha.save(saida, "JPEG", quality=85)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roteiro", type=Path)
    ap.add_argument("--html-apenas", action="store_true")
    ap.add_argument("--sem-validar-kit", action="store_true",
                    help="só para a prova do brand kit, antes da confirmação humana")
    a = ap.parse_args()

    roteiro = json.loads(a.roteiro.read_text(encoding="utf-8"))
    base = a.roteiro.parent.resolve()
    kit_path = (base / roteiro["brand_kit"]).resolve()
    if not a.sem_validar_kit:
        r = subprocess.run([sys.executable, str(VALIDADOR), "--validar", str(kit_path)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit("brand kit não validado — nenhum criativo antes disso:\n" + r.stdout)
    kit = json.loads(kit_path.read_text(encoding="utf-8"))
    formato = roteiro.get("formato", "feed")
    if formato not in FORMATOS:
        sys.exit(f"formato inválido: {formato} ({', '.join(FORMATOS)})")
    pecas = roteiro["pecas"]
    if not 1 <= len(pecas) <= 10:
        sys.exit("de 1 a 10 peças por roteiro (limite de carrossel da API)")

    htmls = [(f"{i:02d}-{p['template']}", montar_html(p, i, len(pecas), kit, formato, base, kit_path.parent))
             for i, p in enumerate(pecas, 1)]
    saida = base / "render"
    if a.html_apenas:
        saida.mkdir(exist_ok=True)
        for nome, doc in htmls:
            (saida / f"{nome}.html").write_text(doc, encoding="utf-8")
        print(f"{len(htmls)} HTML em {saida}")
        return

    arquivos, relatorio = renderizar(htmls, saida, *FORMATOS[formato])
    folha(arquivos, saida / "folha.jpg")
    (saida / "relatorio.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")

    esperadas = {kit["tipografia"][k]["familia"] for k in ("titulo", "texto")}
    erros = 0
    for r in relatorio:
        faltando = esperadas - set(r["fontes"])
        if faltando:
            print(f"✗ {r['peca']}: fonte não carregou ({', '.join(faltando)}) — o render usou fallback")
            erros += 1
        for av in r["avisos"]:
            print(("✗ " if av["erro"] else "! ") + f"{r['peca']} · {av['campo']}: {av['msg']}")
            erros += av["erro"]
    print(f"{len(arquivos)} peça(s) em {saida} · folha de revisão: {saida / 'folha.jpg'}")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
