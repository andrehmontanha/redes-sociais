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
        env_web = {**env, "ESTUDIO_API_CHAVE": "x" * 32, "ESTUDIO_WEBAPP_URL": "https://exemplo.invalid"}
        rodar("webapp: não envia item alterado depois da aprovação", [PY, SK / "publicar-instagram" / "scripts" / "enviar_webapp.py",
                                                                      "enviar", item], espera=1, env=env_web)
        item2 = rodar("cria item para o webapp", [PY, fila, "criar", "--cliente", "demo", "--tipo", "feed",
                                                  "--midias", jpgs[0], "--legenda", "Teste webapp"], env=env)
        rodar("gera prévia do item do webapp", [PY, fila, "previa", item2], env=env)
        rodar("aprova item do webapp", [PY, fila, "aprovar", item2, "--por", "Teste"], env=env)
        pj2 = Path(item2) / "post.json"
        post2 = json.loads(pj2.read_text())
        post2["webapp"] = {"id": "demo--x", "enviado_em": "2026-10-01T00:00:00", "url": "https://exemplo.invalid/fila/demo--x"}
        pj2.write_text(json.dumps(post2, ensure_ascii=False))
        rodar("publicar.py recusa item entregue ao webapp", [PY, pub, "--simular", "item", item2, "--agora"], espera=1, env=env)
        rodar("recusa legenda com 31 hashtags", [PY, fila, "criar", "--cliente", "demo", "--tipo", "feed", "--midias",
                                                 jpgs[0], "--legenda", " ".join(f"#t{i}" for i in range(31))], espera=1, env=env)

        # conexão com o Instagram (sem rede: link, state e sincronização offline)
        con = SK / "conectar-instagram" / "scripts"
        env_app = {**env, "IG_APP_ID": "123", "IG_APP_SECRET": "segredo", "IG_REDIRECT_URI": "https://exemplo.com/retorno"}
        saida = rodar("gera link de autorização", [PY, con / "conectar.py", "url", "--cliente", "demo"], env=env_app)
        print(("✓" if "instagram.com/oauth/authorize" in saida and "state=" in saida else "✗"), "link com state")
        rodar("recusa retorno com state forjado", [PY, con / "conectar.py", "trocar", "--cliente", "demo", "--retorno",
                                                    "https://exemplo.com/retorno?code=abc&state=forjado"], espera=1, env=env_app)
        rodar("recusa redirect sem HTTPS", [PY, con / "conectar.py", "url", "--cliente", "demo"], espera=1,
              env={**env_app, "IG_REDIRECT_URI": "http://exemplo.com/r"})
        bruto = base / "bruto.json"
        bruto.write_text(json.dumps({
            "perfil": {"username": "demo", "followers_count": 12000, "follows_count": 200, "media_count": 300},
            "midias": [{"id": str(i), "caption": f"post {i} #demo", "media_type": "IMAGE" if i % 2 else "VIDEO",
                        "media_product_type": "FEED" if i % 2 else "REELS", "permalink": f"https://instagram.com/p/X{i}",
                        "shortcode": f"X{i}", "timestamp": f"2026-09-{10 + i:02d}T21:00:00+0000",
                        "like_count": 100 + i, "comments_count": 5} for i in range(12)],
            "insights": {str(i): {"reach": 1000 * (i + 1), "saved": 10 + i, "shares": 5 + i, "views": 3000,
                                  "likes": 100 + i, "comments": 5} for i in range(12)},
            "conta_insights": {"reach": 50000}}))
        rodar("sincroniza (offline)", [PY, con / "sincronizar.py", "--cliente", "demo", "--de-arquivo", bruto,
                                       "--nicho", "turismo_hotelaria"], env=env)
        dados = next((base / "clientes" / "demo" / "instagram").glob("*/dados_demo.json"))
        rodar("análise aceita os dados sincronizados", [PY, SK / "analise-perfil-instagram" / "scripts" /
                                                         "calcular_metricas.py", dados])
        rodar("recusa dados de outra conta", [PY, con / "sincronizar.py", "--cliente", "outro", "--de-arquivo", bruto],
              espera=1, env=env)

        # avatares com consentimento (API simulada)
        av = SK / "avatares" / "scripts" / "avatar.py"
        termo = base / "termo.pdf"
        termo.write_bytes(b"%PDF-1.4 termo assinado " + b"x" * 2000)
        reg = ["registrar", "--cliente", "demo", "--nome", "Ana Souza", "--contato", "ana@exemplo.com",
               "--termo", termo, "--assinado-em", "2026-09-01", "--validade", "2027-08-31",
               "--usos", "institucional,oferta", "--voz", "sim"]
        rodar("recusa avatar sem declaração de maioridade", [PY, av, *reg], espera=1, env=env)
        rodar("recusa validade acima de 24 meses", [PY, av, *reg[:-6], "--validade", "2029-01-01", "--usos",
                                                     "oferta", "--voz", "sim", "--maior-de-idade"], espera=1, env=env)
        rodar("registra termo de consentimento", [PY, av, *reg, "--maior-de-idade"], env=env)
        gravacao = base / "clientes" / "demo" / "avatares" / "ana-souza" / "gravacao" / "treino.mp4"
        gravacao.parent.mkdir(parents=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=20",
                        "-f", "lavfi", "-i", "sine=f=200:d=20", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(gravacao)], check=True)
        rodar("recusa gerar antes do consentimento", [PY, av, "--simular", "gerar", "--cliente", "demo", "--pessoa",
                                                       "ana-souza", "--uso", "oferta", "--roteiro", termo, "--nome", "x"],
              espera=1, env=env)
        rodar("envia treino (simulado)", [PY, av, "--simular", "criar", "--cliente", "demo", "--pessoa", "ana-souza",
                                          "--video", gravacao], env=env)
        rodar("gera link de consentimento (simulado)", [PY, av, "--simular", "consentimento", "--cliente", "demo",
                                                         "--pessoa", "ana-souza"], env=env)
        rodar("ativa após treino e consentimento", [PY, av, "--simular", "status", "--cliente", "demo"], env=env)
        fala = base / "fala.txt"
        fala.write_text("Vote no nosso candidato e venha para o resort!")
        rodar("recusa roteiro com tema vedado", [PY, av, "--simular", "gerar", "--cliente", "demo", "--pessoa",
                                                  "ana-souza", "--uso", "oferta", "--roteiro", fala, "--nome", "x"],
              espera=1, env=env)
        fala.write_text("Oi! Os pacotes de outubro já estão abertos. Reserve pelo link da bio.")
        rodar("recusa uso fora do termo", [PY, av, "--simular", "gerar", "--cliente", "demo", "--pessoa", "ana-souza",
                                            "--uso", "evento", "--roteiro", fala, "--nome", "x"], espera=1, env=env)
        rodar("gera vídeo do avatar (simulado, WebM com alfa)", [PY, av, "--simular", "gerar", "--cliente", "demo",
                                                                  "--pessoa", "ana-souza", "--uso", "oferta", "--roteiro",
                                                                  fala, "--nome", "oferta-outubro", "--transparente"], env=env)
        webm = next((base / "clientes" / "demo" / "avatares" / "ana-souza" / "videos").glob("*.webm"))
        r2 = cli / "criativos" / "r2"
        r2.mkdir()
        (r2 / "roteiro-video.json").write_text(json.dumps({"brand_kit": "../../brand-kit.json", "trilha": "ambiente-calmo",
            "cenas": [{"tipo": "avatar", "midia": f"../../avatares/ana-souza/videos/{webm.name}",
                       "fundo": "../../referencias/cliente/post01.jpg", "texto": "Pacotes de outubro"},
                      {"tipo": "cta", "titulo": "Reserve pelo link da bio", "duracao": 2.5}]}, ensure_ascii=False))
        montar = SK / "criativos-video" / "scripts" / "montar_reel.py"
        rodar("monta Reel com avatar", [PY, montar, r2 / "roteiro-video.json"], env=env)
        if a.com_video and (r2 / "video").exists():
            v2 = r2 / "video"
            rodar("hyperframes check (avatar)", ["npx", "--yes", "hyperframes@0.8.90", "check"], cwd=v2)
            rodar("hyperframes render (avatar)", ["npx", "--yes", "hyperframes@0.8.90", "render", "-o", "reel-mudo.mp4"], cwd=v2)
            rodar("sonoriza Reel com voz do avatar", [PY, SK / "efeitos-sonoros" / "scripts" / "mixar_sfx.py",
                                                      v2 / "reel-mudo.mp4", v2 / "deixas.json", "--saida", v2 / "reel.mp4"])
            item = rodar("fila detecta avatar e põe aviso de IA", [PY, fila, "criar", "--cliente", "demo", "--tipo", "reel",
                                                                    "--midias", v2 / "reel.mp4", "--legenda", "Outubro!"], env=env)
            post = json.loads((Path(item) / "post.json").read_text())
            ok = post["avatares"] == ["ana-souza"] and "criado com IA" in post["legenda"]
            print(("✓" if ok else "✗"), "post marcado com avatar e aviso na legenda")
            if not ok:
                falhas.append("aviso de IA")
            rodar("prévia do post com avatar", [PY, fila, "previa", item], env=env)
            rodar("recusa aprovar sem a pessoa retratada", [PY, fila, "aprovar", item, "--por", "Gestor"], espera=1, env=env)
            rodar("aprova com a pessoa retratada", [PY, fila, "aprovar", item, "--por", "Gestor", "--pessoas", "Ana Souza"],
                  env=env)
            rodar("revoga consentimento", [PY, av, "--simular", "revogar", "--cliente", "demo", "--pessoa", "ana-souza",
                                           "--motivo", "pedido da pessoa"], env=env)
            rodar("publicação bloqueada após revogação", [PY, pub, "--simular", "item", item, "--agora"], espera=1, env=env)
            post = json.loads((Path(item) / "post.json").read_text())
            print(("✓" if post["status"] == "cancelado" else "✗"), "item da fila cancelado pela revogação")
            if post["status"] != "cancelado":
                falhas.append("cancelamento por revogação")
        rodar("recusa montar Reel com avatar revogado" if a.com_video else "monta de novo (ainda ativo)",
              [PY, montar, r2 / "roteiro-video.json"], espera=1 if a.com_video else 0, env=env)
    finally:
        if a.manter:
            print("pasta do teste:", base)
        else:
            shutil.rmtree(base, ignore_errors=True)

    print(f"\n{'tudo certo' if not falhas else f'{len(falhas)} falha(s): ' + ', '.join(falhas)}")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
