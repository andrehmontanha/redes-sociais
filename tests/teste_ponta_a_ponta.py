#!/usr/bin/env python3
"""Teste de ponta a ponta do estúdio com um cliente sintético.

Uso:
    python tests/teste_ponta_a_ponta.py              # imagem, som, fila, publicação simulada
    python tests/teste_ponta_a_ponta.py --com-video  # + Reel com HyperFrames (npx, ~1 min)

Não publica nada e não precisa de credenciais: a publicação roda em --simular.
Tudo acontece numa pasta temporária apagada no fim (--manter para inspecionar).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SK = RAIZ / ".claude" / "skills"
PY = sys.executable
falhas = []


def rodar(nome, cmd, espera=0, cwd=None, env=None):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=cwd,
                       env={**os.environ, **(env or {})})
    ok = r.returncode == espera
    print(("✓" if ok else "✗"), nome)
    if not ok:
        falhas.append(nome)
        print("   saída:", r.returncode, "\n  ", (r.stdout + r.stderr)[-1500:].replace("\n", "\n   "))
    return r.stdout.strip()


def cliente_sintetico(base: Path):
    from PIL import Image, ImageDraw
    import random
    random.seed(3)
    refs = base / "clientes" / "demo" / "referencias" / "cliente"
    refs.mkdir(parents=True)
    pal = [(246, 239, 228), (28, 61, 52), (214, 120, 64), (120, 150, 110)]
    for i in range(10):
        im = Image.new("RGB", (1080, 1350), pal[0] if i % 2 == 0 else pal[3])
        d = ImageDraw.Draw(im)
        for _ in range(12):
            x, y = random.randint(0, 900), random.randint(0, 1200)
            d.ellipse([x, y, x + random.randint(80, 400), y + random.randint(80, 400)], fill=random.choice(pal))
        im.save(refs / f"post{i:02d}.jpg", quality=90)
    return base / "clientes" / "demo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--com-video", action="store_true")
    ap.add_argument("--manter", action="store_true")
    a = ap.parse_args()

    base = Path(tempfile.mkdtemp(prefix="estudio-teste-"))
    env = {"ESTUDIO_RAIZ": str(base)}
    try:
        cli = cliente_sintetico(base)
        kit = cli / "brand-kit.json"
        ext = SK / "identidade-visual" / "scripts" / "extrair_identidade.py"

        # identidade
        rodar("mede a identidade", [PY, ext, cli / "referencias" / "cliente", "--handle", "demo", "--saida", kit])
        rodar("kit rascunho é bloqueado", [PY, ext, "--validar", kit], espera=1)
        rodar("não sobrescreve kit existente", [PY, ext, cli / "referencias" / "cliente", "--handle", "demo",
                                               "--saida", kit], espera=1)
        k = json.loads(kit.read_text())
        k["cores"]["papeis"] = {"fundo": "#f6efe4", "primaria": "#1c3d34", "destaque": "#d67841",
                                "texto": "#1c3d34", "texto_sobre_foto": "#ffffff", "texto_sobre_destaque": "#f6efe4"}
        k["tipografia"] = {"origem": "observado",
                           "titulo": {"familia": "Playfair Display", "peso": 700, "caixa": "normal", "google_fonts": True},
                           "texto": {"familia": "Inter", "peso": 400, "google_fonts": True}}
        k["composicao"] = {"origem": "observado", "alinhamento": "esquerda", "margem_px": 72, "raio_borda_px": 16,
                           "texto_sobre_foto": "degrade", "densidade_texto": "media"}
        k["elementos"] = {"origem": "observado", "logo": None, "assinatura": "@demo", "recorrentes": []}
        k["voz"] = {"origem": "observado", "tom": "acolhedor", "pessoa": "nós → você", "emojis": "pontual",
                    "hashtags_fixas": ["#demo"], "cta_preferido": "Reserve pelo link da bio", "palavras_evitar": []}
        k["video"] = {"origem": "observado", "ritmo_corte_s": 1.8, "legenda_na_tela": "sempre",
                      "estilo_movimento": "sobrio", "sfx_familia": "sutil"}
        k["confirmado_por"] = "teste automatizado"
        k["referencias_aprovadas"] = ["post00.jpg", "post01.jpg", "post02.jpg"]
        kit.write_text(json.dumps(k, ensure_ascii=False, indent=2))
        rodar("recusa botão com contraste baixo", [PY, ext, "--validar", kit], espera=1)
        k["cores"]["papeis"]["texto_sobre_destaque"] = "#1c3d34"
        kit.write_text(json.dumps(k, ensure_ascii=False, indent=2))
        rodar("kit completo é aceito", [PY, ext, "--validar", kit])

        # imagem
        c1 = cli / "criativos" / "c1"
        c1.mkdir(parents=True)
        (c1 / "roteiro.json").write_text(json.dumps({"brand_kit": "../../brand-kit.json", "formato": "feed", "pecas": [
            {"template": "capa-carrossel", "campos": {"rotulo": "Guia", "titulo": "5 motivos para vir",
                                                      "foto": "../../referencias/cliente/post01.jpg"}},
            {"template": "lista", "campos": {"titulo": "Incluso", "itens": ["Café", "Piscinas", "Late checkout"]}},
            {"template": "texto-destaque", "campos": {"titulo": "38 °C direto da fonte"}},
            {"template": "citacao", "campos": {"citacao": "Voltamos pela terceira vez.", "autor": "Mariana S."}},
            {"template": "foto-titulo", "campos": {"titulo": "Seu domingo", "foto": "../../referencias/cliente/post03.jpg"}},
            {"template": "oferta", "campos": {"titulo": "2 noites", "preco": "R$ 890", "cta": "Reserve"}},
        ]}, ensure_ascii=False))
        render = SK / "criativos-imagem" / "scripts" / "renderizar_criativo.py"
        rodar("renderiza carrossel de 6 peças", [PY, render, c1 / "roteiro.json"])
        n = len(list((c1 / "render").glob("0*.jpg")))
        print(("✓" if n == 6 else "✗"), f"6 JPEG gerados ({n})")
        if n != 6:
            falhas.append("contagem de JPEG")

        fora = base / "fora.jpg"
        shutil.copy(cli / "referencias" / "cliente" / "post00.jpg", fora)
        c2 = cli / "criativos" / "c2"
        c2.mkdir()
        (c2 / "roteiro.json").write_text(json.dumps({"brand_kit": "../../brand-kit.json", "pecas": [
            {"template": "foto-titulo", "campos": {"titulo": "x", "foto": str(fora)}}]}))
        rodar("recusa foto fora da pasta do cliente", [PY, render, c2 / "roteiro.json"], espera=1)

        # som
        cat = SK / "efeitos-sonoros" / "scripts" / "catalogo.py"
        rodar("catálogo de sons íntegro", [PY, cat, "validar"])
        mudo = base / "mudo.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=0x1c3d34:s=1080x1920:d=6:r=30",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mudo)], check=True)
        deixas = base / "deixas.json"
        deixas.write_text(json.dumps({"trilha": {"id": "pulso-leve-100bpm", "ganho_db": -4},
                                      "deixas": [{"t": 0, "sfx": "pop"}, {"t": 2, "sfx": "swipe"}, {"t": 4, "sfx": "ding"}]}))
        final = base / "final.mp4"
        rodar("mixa trilha e efeitos", [PY, SK / "efeitos-sonoros" / "scripts" / "mixar_sfx.py", mudo, deixas, "--saida", final])
        rodar("vídeo mixado dentro da especificação", [PY, SK / "criativos-video" / "scripts" / "validar_reel.py", final])

        # vídeo com HyperFrames
        if a.com_video:
            r1 = cli / "criativos" / "r1"
            r1.mkdir()
            (r1 / "roteiro-video.json").write_text(json.dumps({"brand_kit": "../../brand-kit.json", "trilha": "ambiente-calmo",
                "cenas": [{"tipo": "foto", "midia": "../../referencias/cliente/post01.jpg", "duracao": 2.4, "texto": "Gancho"},
                          {"tipo": "texto", "titulo": "Direto da fonte", "duracao": 2.4},
                          {"tipo": "cta", "titulo": "Reserve pelo link da bio", "duracao": 2.5}]}, ensure_ascii=False))
            rodar("monta projeto HyperFrames", [PY, SK / "criativos-video" / "scripts" / "montar_reel.py", r1 / "roteiro-video.json"])
            v = r1 / "video"
            if not v.exists():
                print("  (pulando o resto do vídeo: projeto não foi montado)")
                a.com_video = False
        if a.com_video:
            rodar("hyperframes check", ["npx", "--yes", "hyperframes@0.8.90", "check"], cwd=v)
            rodar("hyperframes render", ["npx", "--yes", "hyperframes@0.8.90", "render", "-o", "reel-mudo.mp4"], cwd=v)
            rodar("sonoriza o Reel", [PY, SK / "efeitos-sonoros" / "scripts" / "mixar_sfx.py", v / "reel-mudo.mp4",
                                      v / "deixas.json", "--saida", v / "reel.mp4"])
            rodar("Reel dentro da especificação", [PY, SK / "criativos-video" / "scripts" / "validar_reel.py", v / "reel.mp4"])

        # fila e publicação
        fila = SK / "publicar-instagram" / "scripts" / "fila.py"
        pub = SK / "publicar-instagram" / "scripts" / "publicar.py"
        jpgs = sorted((c1 / "render").glob("0*.jpg"))
        item = rodar("cria item na fila", [PY, fila, "criar", "--cliente", "demo", "--tipo", "carrossel",
                                          "--midias", *jpgs, "--legenda", "Teste #demo"], env=env)
        rodar("recusa publicar sem aprovação", [PY, pub, "--simular", "item", item, "--agora"], espera=1, env=env)
        rodar("recusa aprovar sem prévia", [PY, fila, "aprovar", item, "--por", "Teste"], espera=1, env=env)
        rodar("gera prévia", [PY, fila, "previa", item], env=env)
        rodar("registra aprovação", [PY, fila, "aprovar", item, "--por", "Teste"], env=env)
        rodar("publica (simulado)", [PY, pub, "--simular", "item", item, "--agora"], env=env)
        pj = Path(item) / "post.json"
        post = json.loads(pj.read_text())
        post["legenda"] += " (editada depois)"
        pj.write_text(json.dumps(post, ensure_ascii=False))
        rodar("recusa item alterado depois da aprovação", [PY, pub, "--simular", "item", item, "--agora"], espera=1, env=env)
        rodar("recusa legenda com 31 hashtags", [PY, fila, "criar", "--cliente", "demo", "--tipo", "feed", "--midias",
                                                 jpgs[0], "--legenda", " ".join(f"#t{i}" for i in range(31))], espera=1, env=env)
    finally:
        if a.manter:
            print("pasta do teste:", base)
        else:
            shutil.rmtree(base, ignore_errors=True)

    print(f"\n{'tudo certo' if not falhas else f'{len(falhas)} falha(s): ' + ', '.join(falhas)}")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
