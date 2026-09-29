#!/usr/bin/env python3
"""Avatares digitais de pessoas reais do perfil — só com consentimento, só maiores
de idade, revogáveis a qualquer momento. Motor: HeyGen (digital twin + Avatar V).

Uso:
    python avatar.py registrar --cliente <h> --nome "Nome Completo" --contato "email/whats" \\
        --papel "recepcionista" --termo termo-assinado.pdf --assinado-em 2026-09-29 \\
        --validade 2027-09-29 --usos institucional,oferta,dicas --voz sim --maior-de-idade \\
        [--proibido "concorrente X"] [--exige-aprovacao sim]
    python avatar.py criar         --cliente <h> --pessoa <slug> --video gravacao.mp4
    python avatar.py consentimento --cliente <h> --pessoa <slug>      # link p/ a pessoa gravar a declaração no HeyGen
    python avatar.py status        --cliente <h> [--pessoa <slug>]
    python avatar.py gerar         --cliente <h> --pessoa <slug> --uso oferta --roteiro fala.txt \\
        --nome oferta-outubro [--transparente] [--engine avatar_v] [--voice-id <id>]
    python avatar.py revogar       --cliente <h> --pessoa <slug> --motivo "pedido da pessoa em 30/09"
    python avatar.py listar        --cliente <h>
    Todo comando aceita --simular (não chama a API).

Estados: termo_registrado → treinando → aguardando_consentimento → ativo
                                                        ↘ revogado / expirado (terminais)

Travas (código de saída 1):
    registrar  — sem termo assinado, sem declaração de maioridade, validade > 24 meses ou
                 uso fora do vocabulário
    criar      — gravação fora de 15–600 s ou sem áudio; arquivo fora da pasta do cliente
    gerar      — avatar não ativo, termo vencido, uso não autorizado, roteiro com tema
                 proibido, voz clonada sem autorização de voz
    revogar    — apaga o avatar no HeyGen, cancela na fila tudo que não foi publicado e
                 lista o que já foi publicado para remoção

Chave: HEYGEN_API_KEY no .env (nunca no chat).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SKILLS = AQUI.parents[1]
RAIZ = Path(os.environ.get("ESTUDIO_RAIZ", AQUI.parents[3]))
API = "https://api.heygen.com"
USOS = {"institucional", "oferta", "dicas", "bastidores", "boas-vindas", "evento"}
TERMINAIS = {"revogado", "expirado"}
# Temas vedados em qualquer termo. É rede de segurança — a trava principal é o
# humano aprovando o roteiro; mas nenhum roteiro com estes temas chega à API.
PROIBIDOS_BASE = {
    "política/eleição": r"\b(vot[eoa]r?|elei[çc][ãa]o|candidat[oa]|partido|deputad|prefeit[oa] .*vote)\b",
    "religião": r"\b(igreja do|converta-se|aceite jesus|orixá|pastor [A-Z])\b",
    "promessa de saúde": r"\b(cura|curar|tratamento garantido|emagre[çc]a|milagr)\w*",
    "falso depoimento": r"\b(eu me hospedei|fiquei hospedad[oa]|como cliente,? eu|minha experi[êe]ncia como h[óo]spede)\b",
    "conteúdo sexual": r"\b(sexy|sensual|nud[ea])\w*",
}


def carregar_env():
    arq = RAIZ / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def slug(texto):
    s = unicodedata.normalize("NFD", texto.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40]


def agora():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha(arq: Path):
    return hashlib.sha256(arq.read_bytes()).hexdigest()


def pasta(cliente, pessoa):
    return RAIZ / "clientes" / cliente / "avatares" / pessoa


def ler(cliente, pessoa):
    arq = pasta(cliente, pessoa) / "registro.json"
    if not arq.exists():
        sys.exit(f"sem registro de avatar para '{pessoa}' em @{cliente} — `avatar.py registrar` primeiro")
    return json.loads(arq.read_text(encoding="utf-8"))


def gravar(reg):
    arq = pasta(reg["cliente"], reg["pessoa"]["slug"]) / "registro.json"
    arq.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def evento(reg, texto):
    reg["historico"].append({"em": agora(), "evento": texto})


def ffprobe(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(arq)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


# ---------------------------------------------------------------- HeyGen

class HeyGen:
    def __init__(self, simular=False):
        self.simular = simular
        self.chave = os.environ.get("HEYGEN_API_KEY")
        if not simular and not self.chave:
            sys.exit("HEYGEN_API_KEY ausente no .env (references/heygen.md)")

    def chamar(self, metodo, caminho, corpo=None):
        if self.simular:
            print(f"  [simulado] {metodo} {API}{caminho} {json.dumps(corpo, ensure_ascii=False)[:160] if corpo else ''}")
            n = int(time.time() * 1000) % 100000
            return {"avatar_item": {"id": f"look_sim{n}", "default_voice_id": f"voice_sim{n}"},
                    "avatar_group": {"id": f"group_sim{n}", "consent_status": "pending"},
                    "url": "https://heygen.com/consent/SIMULADO", "video_id": f"v_sim{n}",
                    "status": "completed", "consent_status": "accepted", "video_url": None}
        import requests
        cab = {"x-api-key": self.chave, "Content-Type": "application/json"}
        for tentativa in range(4):
            r = requests.request(metodo, API + caminho, headers=cab, json=corpo, timeout=120)
            if r.status_code not in (429, 500, 502, 503, 504):
                break
            time.sleep(int(r.headers.get("Retry-After", 2 ** (tentativa + 1))))
        dados = r.json() if r.content and "json" in r.headers.get("content-type", "") else {}
        if r.status_code >= 400:
            erro = dados.get("error", {})
            raise RuntimeError(f"HeyGen {r.status_code} em {caminho}: {erro.get('message', r.text[:300])}")
        return dados.get("data", dados)


# ---------------------------------------------------------------- verificação (usada por outras skills)

def verificar_uso(cliente, pessoa, uso=None, hoje=None):
    """Lista de impedimentos para usar o avatar agora. Vazia = liberado."""
    arq = pasta(cliente, pessoa) / "registro.json"
    if not arq.exists():
        return [f"avatar '{pessoa}' sem registro de consentimento"]
    reg = json.loads(arq.read_text(encoding="utf-8"))
    hoje = hoje or date.today()
    erros = []
    if reg["status"] in TERMINAIS:
        erros.append(f"avatar de {reg['pessoa']['nome']} está {reg['status']}")
    elif reg["status"] != "ativo":
        erros.append(f"avatar de {reg['pessoa']['nome']} ainda não está ativo ({reg['status']})")
    if date.fromisoformat(reg["termo"]["validade_ate"]) < hoje:
        erros.append(f"termo de {reg['pessoa']['nome']} venceu em {reg['termo']['validade_ate']}")
    if uso and uso not in reg["termo"]["usos_permitidos"]:
        erros.append(f"uso '{uso}' não autorizado no termo de {reg['pessoa']['nome']} "
                     f"(autorizados: {', '.join(reg['termo']['usos_permitidos'])})")
    if "instagram" not in reg["termo"]["canais"]:
        erros.append("termo não autoriza o canal instagram")
    termo = pasta(cliente, pessoa) / reg["termo"]["arquivo"]
    if not termo.exists() or sha(termo) != reg["termo"]["sha256"]:
        erros.append("arquivo do termo ausente ou alterado depois do registro")
    return erros


def checar_roteiro(texto, reg):
    achados = []
    baixo = texto.lower()
    for tema, padrao in PROIBIDOS_BASE.items():
        if re.search(padrao, baixo, flags=re.I):
            achados.append(tema)
    for termo in reg["termo"].get("usos_proibidos_extra", []):
        if termo.lower() in baixo:
            achados.append(f"vedado no termo: {termo}")
    return achados


# ---------------------------------------------------------------- comandos

def cmd_registrar(a):
    if not a.maior_de_idade:
        sys.exit("sem --maior-de-idade: avatar só de pessoas com 18 anos ou mais. Nunca de criança "
                 "ou adolescente, nem com autorização dos pais.")
    termo = Path(a.termo)
    if not termo.exists() or termo.stat().st_size < 1000:
        sys.exit("termo assinado não encontrado (ou vazio) — sem termo não há registro")
    if termo.suffix.lower() not in {".pdf", ".jpg", ".jpeg", ".png"}:
        sys.exit("termo precisa ser PDF ou imagem do documento assinado")
    assinado = date.fromisoformat(a.assinado_em)
    validade = date.fromisoformat(a.validade)
    if assinado > date.today():
        sys.exit("data de assinatura no futuro")
    if validade <= date.today():
        sys.exit("validade já passou")
    if (validade - assinado).days > 731:
        sys.exit("validade acima de 24 meses — renove o termo em vez de estender")
    usos = [u.strip() for u in a.usos.split(",") if u.strip()]
    fora = [u for u in usos if u not in USOS]
    if fora or not usos:
        sys.exit(f"usos fora do vocabulário: {fora or '(vazio)'} — use {', '.join(sorted(USOS))}")
    s = slug(a.nome)
    dest = pasta(a.cliente, s)
    if (dest / "registro.json").exists():
        sys.exit(f"'{s}' já registrado — para novo termo, revogue o anterior ou registre com outro nome")
    dest.mkdir(parents=True)
    copia = dest / f"termo{termo.suffix.lower()}"
    shutil.copy2(termo, copia)
    reg = {
        "cliente": a.cliente,
        "pessoa": {"nome": a.nome.strip(), "slug": s, "contato": a.contato, "papel": a.papel},
        "maior_de_idade": True,
        "termo": {"arquivo": copia.name, "sha256": sha(copia), "assinado_em": assinado.isoformat(),
                  "validade_ate": validade.isoformat(), "voz_clonada": a.voz == "sim",
                  "canais": [c.strip() for c in a.canais.split(",")], "usos_permitidos": usos,
                  "usos_proibidos_extra": [p.strip() for p in (a.proibido or "").split(",") if p.strip()],
                  "exige_aprovacao_da_pessoa": a.exige_aprovacao == "sim"},
        "heygen": {}, "status": "termo_registrado", "usos": [],
        "historico": [{"em": agora(), "evento": "termo registrado"}],
    }
    gravar(reg)
    print(f"✓ registro criado para {a.nome} ('{s}') · "
          f"válido até {validade:%d/%m/%Y} · usos: {', '.join(usos)} · voz clonada: {a.voz}")
    print(f"  próximo: gravação de treino (references/gravacao.md) → avatar.py criar --pessoa {s}")


def cmd_criar(a):
    reg = ler(a.cliente, a.pessoa)
    if reg["status"] in TERMINAIS:
        sys.exit(f"registro {reg['status']} — não se cria avatar")
    if reg["heygen"].get("group_id"):
        sys.exit("avatar já criado para este registro (veja `status`)")
    video = Path(a.video).resolve()
    raiz_cliente = (RAIZ / "clientes" / a.cliente).resolve()
    if raiz_cliente not in video.parents:
        sys.exit(f"gravação fora da pasta do cliente ({raiz_cliente})")
    info = ffprobe(video)
    dur = float(info["format"]["duration"])
    if not 15 <= dur <= 600:
        sys.exit(f"gravação com {dur:.0f}s — o HeyGen exige de 15 a 600 s (ideal 2 a 5 min)")
    if not any(s["codec_type"] == "audio" for s in info["streams"]):
        sys.exit("gravação sem áudio — o treino precisa de fala audível")
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    menor = min(int(v["width"]), int(v["height"]))
    if menor < 1080:
        print(f"! resolução {v['width']}×{v['height']} — abaixo de 1080 p o avatar perde nitidez")
    if dur < 90:
        print(f"! {dur:.0f}s de fala — funciona, mas 2 a 5 min dão avatar mais natural")
    sys.path.insert(0, str(SKILLS / "publicar-instagram" / "scripts"))
    import hospedar
    url = hospedar.subir(video, f"avatares/{a.cliente}/{a.pessoa}/{video.name}", a.simular)
    hg = HeyGen(a.simular)
    d = hg.chamar("POST", "/v3/avatars", {"type": "digital_twin", "name": f"{reg['pessoa']['nome']} · {a.cliente}",
                                           "file": {"type": "url", "url": url}})
    reg["heygen"] = {"group_id": d["avatar_group"]["id"], "look_id": d["avatar_item"]["id"],
                     "voice_id": d["avatar_item"].get("default_voice_id"), "treino": video.name,
                     "treino_sha256": sha(video), "treino_s": round(dur, 1)}
    reg["status"] = "treinando"
    evento(reg, f"treino enviado ({dur:.0f}s)")
    gravar(reg)
    if not a.simular:
        hospedar.limpar(f"avatares/{a.cliente}/{a.pessoa}")
    print(f"✓ treino enviado · look {reg['heygen']['look_id']}")
    print(f"  próximo: avatar.py consentimento --cliente {a.cliente} --pessoa {a.pessoa}")


def cmd_consentimento(a):
    reg = ler(a.cliente, a.pessoa)
    if reg["status"] in TERMINAIS or not reg["heygen"].get("group_id"):
        sys.exit(f"status {reg['status']} — consentimento só depois de `criar`")
    d = HeyGen(a.simular).chamar("POST", f"/v3/avatars/{reg['heygen']['group_id']}/consent", {})
    reg["heygen"]["consent_url_criado_em"] = agora()
    reg["status"] = "aguardando_consentimento" if reg["status"] == "treinando" else reg["status"]
    evento(reg, "link de consentimento HeyGen gerado")
    gravar(reg)
    primeiro = reg["pessoa"]["nome"].split()[0]
    print(f"Envie SÓ para {reg['pessoa']['nome']} ({reg['pessoa']['contato']}) — vale 24 h, uma gravação:\n")
    print(f"Oi, {primeiro}! Para ativar seu avatar digital no Instagram da marca, conforme o termo que você "
          f"assinou, abra este link e grave a declaração de consentimento (1 minuto, com câmera e microfone): "
          f"{d.get('url')}\nVocê pode revogar a autorização quando quiser, é só avisar.")


def cmd_status(a):
    pessoas = [a.pessoa] if a.pessoa else sorted(p.name for p in (RAIZ / "clientes" / a.cliente / "avatares").glob("*")
                                                 if (p / "registro.json").exists())
    hg = None
    for p in pessoas:
        reg = ler(a.cliente, p)
        if reg["status"] not in TERMINAIS and reg["heygen"].get("group_id"):
            hg = hg or HeyGen(a.simular)
            grupo = hg.chamar("GET", f"/v3/avatars/{reg['heygen']['group_id']}")
            look = hg.chamar("GET", f"/v3/avatars/looks/{reg['heygen']['look_id']}")
            reg["heygen"]["consent_status"] = grupo.get("consent_status")
            reg["heygen"]["look_status"] = look.get("status")
            if look.get("status") == "failed":
                evento(reg, f"treino falhou: {look.get('error', {}).get('message')}")
            if look.get("status") == "completed" and grupo.get("consent_status") == "accepted" \
                    and reg["status"] != "ativo":
                reg["status"] = "ativo"
                evento(reg, "avatar ativo (treino concluído e consentimento aceito no HeyGen)")
        if reg["status"] not in TERMINAIS and date.fromisoformat(reg["termo"]["validade_ate"]) < date.today():
            reg["status"] = "expirado"
            evento(reg, "termo vencido")
        gravar(reg)
        h = reg["heygen"]
        print(f"{p:24s} {reg['status']:26s} treino={h.get('look_status', '-'):11s} "
              f"consentimento={h.get('consent_status', '-'):9s} válido até {reg['termo']['validade_ate']}")
    if not pessoas:
        print("nenhum avatar registrado")


def cmd_gerar(a):
    reg = ler(a.cliente, a.pessoa)
    erros = verificar_uso(a.cliente, a.pessoa, a.uso)
    roteiro = Path(a.roteiro).read_text(encoding="utf-8").strip()
    if not roteiro:
        erros.append("roteiro vazio")
    if len(roteiro) > 1500:
        erros.append(f"roteiro com {len(roteiro)} caracteres — máx. 1500 (~90 s de fala)")
    erros += [f"roteiro com tema vedado: {t}" for t in checar_roteiro(roteiro, reg)]
    voz = a.voice_id or reg["heygen"].get("voice_id")
    if not a.voice_id and not reg["termo"]["voz_clonada"]:
        erros.append("termo não autoriza voz clonada — passe --voice-id de uma voz de catálogo")
    if erros:
        sys.exit("não gerado:\n  " + "\n  ".join(erros))
    corpo = {"type": "avatar", "avatar_id": reg["heygen"]["look_id"], "voice_id": voz, "script": roteiro,
             "title": f"{a.cliente} · {a.nome}", "resolution": "1080p", "aspect_ratio": "9:16",
             "engine": {"type": a.engine}, "output_format": "webm" if a.transparente else "mp4"}
    hg = HeyGen(a.simular)
    d = hg.chamar("POST", "/v3/videos", corpo)
    vid = d["video_id"]
    inicio = time.time()
    while True:
        st = hg.chamar("GET", f"/v3/videos/{vid}")
        if st.get("status") == "completed":
            break
        if st.get("status") == "failed":
            sys.exit(f"geração falhou: {st.get('failure_message')}")
        if time.time() - inicio > 1800:
            sys.exit(f"geração não terminou em 30 min — consulte depois: GET /v3/videos/{vid}")
        time.sleep(15)
    ext = "webm" if a.transparente else "mp4"
    destino = pasta(a.cliente, a.pessoa) / "videos" / f"{date.today().isoformat()}-{slug(a.nome)}.{ext}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if a.simular:
        # simulação produz um arquivo de teste com o mesmo formato, para o resto do fluxo rodar
        filtro = "color=c=black@0.0:s=1080x1920:r=30:d=4,format=yuva420p" if a.transparente \
            else "color=c=0x333333:s=1080x1920:r=30:d=4"
        cod = ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0"] if a.transparente \
            else ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", filtro, "-f", "lavfi",
                        "-i", "sine=f=220:d=4", *cod, "-c:a", "libopus" if a.transparente else "aac",
                        "-shortest", str(destino)], check=True)
    else:
        import requests
        with requests.get(st["video_url"], stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(destino, "wb") as f:
                for bloco in r.iter_content(1 << 16):
                    f.write(bloco)
    manifesto = {"pessoa": reg["pessoa"]["slug"], "nome": reg["pessoa"]["nome"], "cliente": a.cliente,
                 "uso": a.uso, "roteiro": roteiro, "video_id": vid, "engine": a.engine,
                 "transparente": a.transparente, "gerado_em": agora(), "termo_sha256": reg["termo"]["sha256"],
                 "exige_aprovacao_da_pessoa": reg["termo"]["exige_aprovacao_da_pessoa"],
                 "aviso_ia": "Vídeo com avatar digital criado com IA, com autorização da pessoa retratada."}
    destino.with_suffix(".json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    reg["usos"].append({"em": agora(), "arquivo": destino.name, "uso": a.uso, "video_id": vid})
    evento(reg, f"vídeo gerado: {destino.name} ({a.uso})")
    gravar(reg)
    print(f"✓ {destino}")


def cmd_revogar(a):
    reg = ler(a.cliente, a.pessoa)
    if reg["status"] == "revogado":
        sys.exit("já revogado")
    if reg["heygen"].get("group_id"):
        try:
            HeyGen(a.simular).chamar("DELETE", f"/v3/avatars/{reg['heygen']['group_id']}")
            evento(reg, "avatar e voz apagados no HeyGen")
        except RuntimeError as e:
            evento(reg, f"FALHA ao apagar no HeyGen — refaça: {e}")
            print(f"! não consegui apagar no HeyGen ({e}); o registro fica revogado e o apagamento pendente")
    reg["status"] = "revogado"
    evento(reg, f"revogado: {a.motivo}")
    gravar(reg)
    sys.path.insert(0, str(SKILLS / "publicar-instagram" / "scripts"))
    import fila
    canceladas, publicadas = [], []
    for pj in sorted((RAIZ / "clientes" / a.cliente / "fila").glob("*/post.json")):
        post = json.loads(pj.read_text(encoding="utf-8"))
        if a.pessoa not in post.get("avatares", []):
            continue
        if post["status"] == "publicado":
            publicadas.append(post.get("resultado", {}).get("permalink") or pj.parent.name)
        elif post["status"] not in ("rejeitado", "cancelado"):
            post["status"] = "cancelado"
            post["aprovacao"] = None
            post["historico"].append({"em": agora(), "evento": f"cancelado: consentimento de {reg['pessoa']['nome']} revogado"})
            fila.gravar(pj.parent, post)
            canceladas.append(pj.parent.name)
    print(f"✓ avatar de {reg['pessoa']['nome']} revogado")
    print(f"  fila cancelada: {len(canceladas)} item(ns) {', '.join(canceladas)}")
    if publicadas:
        print("  JÁ PUBLICADOS — avalie a remoção conforme o termo (cláusula 5):")
        for p in publicadas:
            print(f"   - {p}")


def cmd_listar(a):
    for p in sorted((RAIZ / "clientes" / a.cliente / "avatares").glob("*/registro.json")):
        reg = json.loads(p.read_text(encoding="utf-8"))
        print(f"{reg['pessoa']['slug']:24s} {reg['status']:26s} {reg['pessoa']['papel'] or '':18s} "
              f"usos={','.join(reg['termo']['usos_permitidos'])} até {reg['termo']['validade_ate']} "
              f"· {len(reg['usos'])} vídeo(s)")


def main():
    carregar_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simular", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("registrar")
    for arg in ("--cliente", "--nome", "--contato", "--termo", "--assinado-em", "--validade", "--usos"):
        r.add_argument(arg, required=True)
    r.add_argument("--papel", default="")
    r.add_argument("--voz", choices=["sim", "nao"], required=True)
    r.add_argument("--canais", default="instagram")
    r.add_argument("--proibido")
    r.add_argument("--exige-aprovacao", choices=["sim", "nao"], default="sim")
    r.add_argument("--maior-de-idade", action="store_true")
    for nome in ("criar", "consentimento", "revogar"):
        p = sub.add_parser(nome)
        p.add_argument("--cliente", required=True)
        p.add_argument("--pessoa", required=True)
        if nome == "criar":
            p.add_argument("--video", required=True)
        if nome == "revogar":
            p.add_argument("--motivo", required=True)
    s = sub.add_parser("status"); s.add_argument("--cliente", required=True); s.add_argument("--pessoa")
    g = sub.add_parser("gerar")
    for arg in ("--cliente", "--pessoa", "--uso", "--roteiro", "--nome"):
        g.add_argument(arg, required=True)
    g.add_argument("--transparente", action="store_true", help="WebM com alfa, para compor no Reel")
    g.add_argument("--engine", choices=["avatar_v", "avatar_iv", "avatar_iii"], default="avatar_v")
    g.add_argument("--voice-id")
    l = sub.add_parser("listar"); l.add_argument("--cliente", required=True)
    a = ap.parse_args()
    {"registrar": cmd_registrar, "criar": cmd_criar, "consentimento": cmd_consentimento, "status": cmd_status,
     "gerar": cmd_gerar, "revogar": cmd_revogar, "listar": cmd_listar}[a.cmd](a)


if __name__ == "__main__":
    main()
