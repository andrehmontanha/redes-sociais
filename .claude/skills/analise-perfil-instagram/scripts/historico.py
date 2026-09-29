#!/usr/bin/env python3
"""Consolida análises anteriores num histórico comparável.

Uso:
    python historico.py m1.json m2.json m3.json --saida historico.md
    python historico.py --pasta staged/ --cliente thermasdeolimpiaresort --saida historico.md

Recebe saídas de `calcular_metricas.py --json` (de análises de datas e perfis
diferentes) e devolve duas leituras que nenhuma análise isolada dá:

1. **Evolução** — o mesmo perfil ao longo do tempo. É o único jeito de dizer
   "melhorou" com honestidade.
2. **Posição relativa** — o cliente contra os perfis de comparação na data mais
   recente de cada um.

O valor de guardar análise em pasta é exatamente este: sem histórico, toda
análise recomeça do zero e o consultor fica repetindo diagnóstico.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


def carregar(caminhos):
    """Lê os JSON de métricas, tolerando arquivo quebrado sem derrubar tudo."""
    regs, falhas = [], []
    for c in caminhos:
        try:
            d = json.loads(Path(c).read_text(encoding="utf-8"))
            if not d.get("handle"):
                falhas.append((c, "sem campo 'handle'"))
                continue
            eng = d.get("engajamento", {})
            regs.append({
                "handle": d["handle"],
                "data": d.get("coletado_em") or "0000-00-00",
                "seguidores": d.get("seguidores"),
                "er": eng.get("valor_de_referencia"),
                "er_metrica": eng.get("metrica_de_referencia"),
                "classificacao": eng.get("classificacao"),
                "nicho": (eng.get("benchmark") or {}).get("nicho"),
                "piso": (eng.get("benchmark") or {}).get("piso_saudavel"),
                "cadencia": (d.get("cadencia") or {}).get("posts_por_semana"),
                "posts": (d.get("amostra") or {}).get("posts_proprios"),
                "cl": eng.get("comentario_por_curtida_medio"),
                "pilar_top": next(iter((d.get("por_tema") or {}).items()), (None, None))[0],
                "arquivo": str(c),
            })
        except Exception as e:
            falhas.append((c, str(e)[:90]))
    return regs, falhas


def var(antes, depois):
    """Variação percentual legível, com sinal explícito."""
    if antes in (None, 0) or depois is None:
        return "—"
    d = (depois - antes) / abs(antes) * 100
    seta = "▲" if d > 0 else ("▼" if d < 0 else "=")
    return f"{seta} {d:+.0f}%"


def linha_evolucao(r):
    return (f"| {r['data']} | {r['seguidores']:,} | {r['er']}% | "
            f"{r['cadencia']}/sem | {r['posts']} posts |").replace(",", ".")


def montar(regs, cliente=None):
    por_perfil = defaultdict(list)
    for r in regs:
        por_perfil[r["handle"]].append(r)
    for h in por_perfil:
        por_perfil[h].sort(key=lambda x: x["data"])

    # O cliente é quem tem mais análises, salvo indicação explícita.
    if not cliente:
        cliente = max(por_perfil, key=lambda h: len(por_perfil[h]))

    out = [f"# Histórico consolidado — @{cliente}", "",
           f"**Gerado em:** {date.today().strftime('%d/%m/%Y')} · "
           f"{len(regs)} análises · {len(por_perfil)} perfis", ""]

    # ---- 1. Evolução do cliente ----
    hist = por_perfil.get(cliente, [])
    out += ["## Evolução de @" + cliente, ""]
    if len(hist) < 2:
        out += [f"Só há **uma análise** de @{cliente} ({hist[0]['data'] if hist else '—'}). "
                "Evolução exige ao menos duas — esta primeira vira a linha de base contra "
                "a qual as próximas serão medidas.", ""]
    else:
        out += ["| Data | Seguidores | Engajamento | Cadência | Amostra |",
                "|---|---|---|---|---|"]
        out += [linha_evolucao(r) for r in hist]
        a, b = hist[0], hist[-1]
        out += ["", f"**Do primeiro ao último levantamento ({a['data']} → {b['data']}):** "
                    f"seguidores {var(a['seguidores'], b['seguidores'])}, "
                    f"engajamento {var(a['er'], b['er'])}, "
                    f"cadência {var(a['cadencia'], b['cadencia'])}.", ""]
        if b["er"] is not None and a["er"] is not None:
            if b["er"] > a["er"] and (b["seguidores"] or 0) >= (a["seguidores"] or 0):
                out += ["O engajamento subiu **com** a base crescendo — é o cenário bom, "
                        "e o raro: normalmente ER cai à medida que a conta engorda.", ""]
            elif b["er"] < a["er"] and (b["seguidores"] or 0) > (a["seguidores"] or 0):
                out += ["O engajamento caiu enquanto a base cresceu. Isso é o padrão "
                        "esperado e **não é necessariamente piora** — confira se o número "
                        "absoluto de interações subiu antes de tratar como problema.", ""]

    # ---- 2. Posição relativa ----
    #
    # Duas exclusões que evitam um ranking sem sentido:
    #
    # 1. Nicho diferente não compara. ER de tecnologia B2B e ER de turismo vivem
    #    em escalas distintas — é para isso que existe o multiplicador de nicho.
    # 2. Base minúscula não entra. Uma conta de 31 seguidores com 5 curtidas dá
    #    14% de ER e apareceria como "líder", o que é ruído, não desempenho.
    nicho_cliente = por_perfil[cliente][-1].get("nicho")
    outros = [h for h in por_perfil if h != cliente]
    out += ["## Posição relativa", ""]

    def elegivel(r):
        if (r.get("seguidores") or 0) < 1000:
            return False, "base menor que 1.000 — ER estatisticamente inconclusivo"
        if (r.get("posts") or 0) < 5:
            return False, f"amostra de {r.get('posts')} posts — pouco para comparar"
        if nicho_cliente and r.get("nicho") and r["nicho"] != nicho_cliente:
            return False, f"nicho {r['nicho']}, diferente do cliente ({nicho_cliente})"
        return True, None

    comparaveis, fora = [], []
    for h in outros:
        r = por_perfil[h][-1]
        ok, motivo = elegivel(r)
        (comparaveis if ok else fora).append((h, r, motivo))

    # O cliente também passa pelo teste.
    #
    # Sem isso, uma conta de 31 seguidores com 4 curtidas por post sai como
    # "1º de 3 — é o líder do grupo comparado", que é o pior erro possível:
    # a mesma régua que exclui o concorrente pequeno estava promovendo o
    # cliente pequeno, e o número lisonjeia justamente quem menos deveria
    # confiar nele.
    reg_cliente = por_perfil[cliente][-1]
    cliente_ok, motivo_cliente = elegivel(reg_cliente)

    if not comparaveis:
        out += ["Nenhum perfil comparável analisado ainda — sem eles o benchmark é só a "
                "tabela por faixa, que descreve o mercado em geral e não o seu.", ""]
    else:
        out += [f"Perfis do mesmo nicho ({nicho_cliente}), cada um na análise mais recente.", "",
                "| Perfil | Data | Seguidores | Engajamento | Piso do nicho | Cadência |",
                "|---|---|---|---|---|---|"]
        linhas = ([(cliente, reg_cliente)] if cliente_ok else []) + \
                 [(h, r) for h, r, _ in comparaveis]
        for h, r in linhas:
            marca = " **(cliente)**" if h == cliente else ""
            seg = f"{r['seguidores']:,}".replace(",", ".") if r["seguidores"] else "—"
            out.append(f"| @{h}{marca} | {r['data']} | {seg} | {r['er']}% | "
                       f"{r['piso']}% | {r['cadencia']}/sem |")
        ers = [(h, r["er"]) for h, r in linhas if r["er"] is not None]
        if not cliente_ok:
            out += ["", f"**@{cliente} ficou fora do ranking** — {motivo_cliente}. "
                        f"A taxa dele ({reg_cliente['er']}%) existe, mas descreve "
                        "poucas interações numa base minúscula: qualquer curtida a mais "
                        "muda o número em pontos percentuais. Compare cadência, formato "
                        "e pilar; não compare ER.", ""]
        if cliente_ok and len(ers) > 1:
            ers.sort(key=lambda x: -x[1])
            pos = [h for h, _ in ers].index(cliente) + 1
            lider = ers[0]
            out += ["", f"@{cliente} está em **{pos}º de {len(ers)}** em engajamento "
                        f"dentro do nicho." +
                    (f" Líder: @{lider[0]} ({lider[1]}%)." if lider[0] != cliente
                     else " É o líder do grupo comparado."), ""]

    if fora:
        out += ["**Fora da comparação** — analisados, mas não comparáveis com este cliente:", ""]
        out += [f"- @{h} — {motivo}" for h, _, motivo in fora]
        out += ["", "Continuam valendo como referência de formato e de conteúdo; só não "
                    "entram no ranking de engajamento.", ""]

    # ---- 3. Defasagem ----
    out += ["## Frescor dos dados", ""]
    hoje = date.today()
    velhos = []
    for h, rs in sorted(por_perfil.items()):
        try:
            dias = (hoje - date.fromisoformat(rs[-1]["data"])).days
        except Exception:
            continue
        if dias > 30:
            velhos.append(f"- @{h}: última análise há **{dias} dias**")
    if velhos:
        out += ["Estes perfis estão defasados e devem ser recoletados antes de entrar "
                "numa comparação — número velho comparado com número novo produz "
                "conclusão errada:", ""] + velhos + [""]
    else:
        out += ["Todos os perfis têm análise dos últimos 30 dias. Comparação válida.", ""]

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivos", nargs="*", type=Path)
    ap.add_argument("--pasta", type=Path, help="pasta com os JSON de métricas")
    ap.add_argument("--cliente", help="handle do cliente (padrão: quem tem mais análises)")
    ap.add_argument("--saida", type=Path)
    a = ap.parse_args()

    caminhos = list(a.arquivos)
    if a.pasta:
        caminhos += sorted(a.pasta.rglob("*.json"))
    if not caminhos:
        sys.exit("erro: informe arquivos JSON ou --pasta.")

    regs, falhas = carregar(caminhos)
    for c, e in falhas:
        print(f"aviso: ignorado {c}: {e}", file=sys.stderr)
    if not regs:
        sys.exit("erro: nenhum JSON de métricas válido.")

    texto = montar(regs, a.cliente)
    if a.saida:
        a.saida.write_text(texto, encoding="utf-8")
        print(f"histórico: {a.saida} ({len(regs)} análises)")
    else:
        print(texto)


if __name__ == "__main__":
    main()
