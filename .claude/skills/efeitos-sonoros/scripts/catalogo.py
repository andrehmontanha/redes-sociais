#!/usr/bin/env python3
"""Consulta e mantém o catálogo da biblioteca de sons. Todo som tem licença
registrada — sem licença, não entra, e o mixador recusa.

Uso:
    python catalogo.py listar [--tipo sfx|trilha] [--familia sutil|impacto] [--categoria transicao]
    python catalogo.py buscar "transição rápida"
    python catalogo.py adicionar <arquivo> --id nome-curto --tipo sfx --categoria impacto \\
        --familia impacto --uso "..." --licenca cc0 --fonte "https://freesound.org/..." --autor "..."
    python catalogo.py validar

Licenças aceitas:
    propria      — gerado por nós (gerar_biblioteca.py) ou gravado pela equipe
    cc0          — domínio público (Freesound CC0, etc.)
    pixabay      — Pixabay Content License (uso comercial sem crédito; não revender o som isolado)
    comprada     — licença paga (Epidemic, Artlist…): exige --comprovante com o PDF/print da licença
    cliente      — material enviado pelo cliente, que declara ter os direitos
CC-BY e similares exigem crédito na legenda: registre com --credito "texto" e o
publicador acrescenta o crédito automaticamente.
"""

import argparse
import json
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "biblioteca"
CATALOGO = RAIZ / "catalogo.json"
LICENCAS = {"propria", "cc0", "pixabay", "comprada", "cliente", "cc-by"}


def carregar():
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def salvar(cat):
    cat["itens"].sort(key=lambda i: (i["tipo"], i["id"]))
    CATALOGO.write_text(json.dumps(cat, ensure_ascii=False, indent=2), encoding="utf-8")


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def linha(i):
    extra = f"{i.get('bpm', '')} bpm {i.get('clima', '')}" if i["tipo"] == "trilha" else f"{i.get('categoria', '')}/{i.get('familia', '')}"
    return f"{i['id']:22s} {i['tipo']:6s} {i['duracao_s']:6.2f}s  {extra:22s} {i['licenca']['tipo']:8s} {i.get('uso', '')}"


def duracao(arq: Path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                       capture_output=True, text=True)
    return round(float(r.stdout.strip()), 3)


def validar(cat):
    erros = []
    ids = set()
    for i in cat["itens"]:
        if i["id"] in ids:
            erros.append(f"id duplicado: {i['id']}")
        ids.add(i["id"])
        if not (RAIZ / i["arquivo"]).exists():
            erros.append(f"{i['id']}: arquivo ausente ({i['arquivo']})")
        lic = i.get("licenca") or {}
        if lic.get("tipo") not in LICENCAS:
            erros.append(f"{i['id']}: licença ausente ou não aceita ({lic.get('tipo')})")
        if lic.get("tipo") in {"cc0", "pixabay", "cc-by"} and not lic.get("fonte"):
            erros.append(f"{i['id']}: licença {lic['tipo']} sem URL de origem")
        if lic.get("tipo") == "comprada" and not (lic.get("comprovante") and (RAIZ / lic["comprovante"]).exists()):
            erros.append(f"{i['id']}: licença comprada sem comprovante na biblioteca")
        if lic.get("tipo") == "cc-by" and not lic.get("credito"):
            erros.append(f"{i['id']}: CC-BY exige texto de crédito")
    registrados = {i["arquivo"] for i in cat["itens"]}
    for arq in RAIZ.rglob("*"):
        if arq.suffix.lower() in {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}:
            rel = str(arq.relative_to(RAIZ))
            if rel not in registrados:
                erros.append(f"arquivo sem registro no catálogo (não pode ser usado): {rel}")
    return erros


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("listar")
    l.add_argument("--tipo"); l.add_argument("--familia"); l.add_argument("--categoria")
    b = sub.add_parser("buscar"); b.add_argument("termo")
    ad = sub.add_parser("adicionar")
    ad.add_argument("arquivo", type=Path)
    ad.add_argument("--id", required=True)
    ad.add_argument("--tipo", choices=["sfx", "trilha"], required=True)
    ad.add_argument("--categoria"); ad.add_argument("--familia", choices=["sutil", "impacto"])
    ad.add_argument("--clima"); ad.add_argument("--bpm", type=int)
    ad.add_argument("--uso", required=True)
    ad.add_argument("--licenca", choices=sorted(LICENCAS), required=True)
    ad.add_argument("--fonte"); ad.add_argument("--autor"); ad.add_argument("--credito")
    ad.add_argument("--comprovante", type=Path)
    sub.add_parser("validar")
    a = ap.parse_args()
    cat = carregar()

    if a.cmd == "listar":
        for i in cat["itens"]:
            if (a.tipo and i["tipo"] != a.tipo) or (a.familia and i.get("familia") != a.familia) \
                    or (a.categoria and i.get("categoria") != a.categoria):
                continue
            print(linha(i))
    elif a.cmd == "buscar":
        termos = sem_acento(a.termo).split()
        achados = []
        for i in cat["itens"]:
            texto = sem_acento(" ".join(str(v) for k, v in i.items() if k != "licenca"))
            nota = sum(t in texto for t in termos)
            if nota:
                achados.append((nota, i))
        for _, i in sorted(achados, key=lambda x: -x[0]):
            print(linha(i))
        if not achados:
            print("nada encontrado — `listar` mostra tudo")
    elif a.cmd == "adicionar":
        if any(i["id"] == a.id for i in cat["itens"]):
            sys.exit(f"id já existe: {a.id}")
        pasta = RAIZ / ("sfx" if a.tipo == "sfx" else "trilhas")
        destino = pasta / f"{a.id}{a.arquivo.suffix.lower()}"
        shutil.copy2(a.arquivo, destino)
        lic = {"tipo": a.licenca, "fonte": a.fonte, "autor": a.autor, "credito": a.credito,
               "credito_obrigatorio": a.licenca == "cc-by"}
        if a.comprovante:
            comp = RAIZ / "licencas" / f"{a.id}{a.comprovante.suffix}"
            comp.parent.mkdir(exist_ok=True)
            shutil.copy2(a.comprovante, comp)
            lic["comprovante"] = str(comp.relative_to(RAIZ))
        item = {"id": a.id, "tipo": a.tipo, "arquivo": str(destino.relative_to(RAIZ)),
                "duracao_s": duracao(destino), "uso": a.uso, "licenca": {k: v for k, v in lic.items() if v is not None}}
        for k in ("categoria", "familia", "clima", "bpm"):
            if getattr(a, k) is not None:
                item[k] = getattr(a, k)
        cat["itens"].append(item)
        erros = validar({"itens": [item]})
        erros = [e for e in erros if "sem registro" not in e]
        if erros:
            destino.unlink()
            sys.exit("não adicionado:\n  " + "\n  ".join(erros))
        salvar(cat)
        print("adicionado:", linha(item))
    elif a.cmd == "validar":
        erros = validar(cat)
        for e in erros:
            print("✗", e)
        print("✓ catálogo íntegro" if not erros else f"{len(erros)} problema(s)")
        sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
