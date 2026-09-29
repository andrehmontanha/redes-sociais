#!/usr/bin/env python3
"""Compara os anúncios do cliente com os dos concorrentes e gera a seção do HTML.

Uso:
    python anuncios.py dados/anuncios-<handle>.json --resumo
    python anuncios.py dados/anuncios-<handle>.json --html secao-anuncios.html

Existe porque a análise de feed responde "o que ele posta" e nunca "o que ele
compra". Numa execução real, o cliente tinha 22 anúncios ativos no Google, zero
na Meta, e o termo central do negócio dele tinha 280 anúncios ativos de outros
anunciantes. Nenhuma métrica de engajamento mostra isso.

Três decisões embutidas, todas pelo mesmo motivo — não produzir número bonito e
errado:

1. **Contagem de anúncios nunca vira estimativa de verba.** A biblioteca não
   expõe investimento. Muitos anúncios podem ser teste de criativo a R$ 20/dia.
   O que a contagem mede é presença e maturidade operacional, e é assim que sai
   escrito.
2. **Recortes diferentes não se comparam.** No Google, "anúncios do anunciante"
   e "anúncios que apontam para o domínio" dão números distintos para a mesma
   empresa. O script exige o campo `recorte` e se recusa a ranquear misturado.
3. **Tempo no ar pesa mais que quantidade.** Ninguém mantém anúncio ruim
   rodando. O ranking de destaque é por longevidade, não por volume.
"""

import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

ANGULOS = {
    "oferta": "Preço, desconto, parcelamento, prazo",
    "urgencia": "Últimas vagas, acaba hoje, por tempo limitado",
    "prova": "Depoimento, avaliação, número de clientes",
    "institucional": "Marca, história, anos de mercado",
    "destino": "O lugar em si, sem oferta",
    "evento": "Data marcada — feriado, festival, encontro",
}


def dias_no_ar(ad, hoje):
    if ad.get("dias_no_ar") is not None:
        return ad["dias_no_ar"]
    ini = ad.get("inicio_iso")
    if not ini:
        return None
    try:
        return (hoje - date.fromisoformat(ini)).days
    except Exception:
        return None


def carregar(caminho):
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    meta = (d.get("meta") or {}).get("por_anunciante") or []
    goog = (d.get("google") or {}).get("por_anunciante") or []
    termos = (d.get("meta") or {}).get("por_termo") or []

    recortes = {g.get("recorte") for g in goog if g.get("ativos") is not None}
    recortes.discard(None)
    if len(recortes) > 1:
        sys.exit(
            "erro: os anunciantes do Google estão em recortes diferentes "
            f"({', '.join(sorted(recortes))}). 'anunciante' e 'dominio' medem coisas "
            "distintas para a mesma empresa — escolha um e recolete o resto."
        )
    return d, meta, goog, termos, (recortes.pop() if recortes else None)


def consolidar(meta, goog, hoje):
    """Uma linha por marca, com as duas plataformas lado a lado."""
    linhas = {}
    for m in meta:
        k = m.get("handle") or m.get("anunciante")
        linhas.setdefault(k, {"nome": m.get("anunciante") or k,
                              "handle": m.get("handle"),
                              "papel": m.get("papel", "concorrente")})
        linhas[k]["meta_ativos"] = m.get("ativos")
        linhas[k]["meta_lidos"] = m.get("cartoes_lidos")
        ads = m.get("ads") or []
        idades = [d for d in (dias_no_ar(a, hoje) for a in ads) if d is not None]
        linhas[k]["meta_mais_antigo"] = max(idades) if idades else None
        ang = {}
        for a in ads:
            if a.get("angulo"):
                ang[a["angulo"]] = ang.get(a["angulo"], 0) + a.get("reuso", 1)
        linhas[k]["angulos"] = ang
        linhas[k]["ads"] = ads
    for g in goog:
        k = g.get("handle") or g.get("anunciante")
        linhas.setdefault(k, {"nome": g.get("anunciante") or k,
                              "handle": g.get("handle"),
                              "papel": g.get("papel", "concorrente")})
        linhas[k]["google_ativos"] = g.get("ativos")
        linhas[k]["google_verificado"] = g.get("verificado")
        linhas[k]["google_dominio"] = g.get("dominio")
    return linhas


def resumo(linhas, termos, recorte):
    out = []
    cli = [v for v in linhas.values() if v.get("papel") == "cliente"]
    out.append(f"{'marca':28}{'Meta':>7}{'Google':>8}  {'ângulo dominante':22}{'+ antigo':>9}")
    for k, v in sorted(linhas.items(),
                       key=lambda kv: -((kv[1].get("meta_ativos") or 0)
                                        + (kv[1].get("google_ativos") or 0))):
        ang = max(v.get("angulos") or {}, key=(v.get("angulos") or {}).get, default="—")
        marca = ("* " if v.get("papel") == "cliente" else "  ") + v["nome"][:26]
        out.append(f"{marca:28}{str(v.get('meta_ativos','—')):>7}"
                   f"{str(v.get('google_ativos','—')):>8}  {ang:22}"
                   f"{str(v.get('meta_mais_antigo') or '—'):>9}")
    if recorte:
        out.append(f"\nRecorte do Google: {recorte}")
    if termos:
        out.append("\nDisputa por termo (Meta, anúncios ativos):")
        for t in termos:
            marca = "cliente PRESENTE" if t.get("cliente_presente") else "CLIENTE AUSENTE"
            out.append(f"  \"{t['termo']}\": {t['ativos']} anúncios · "
                       f"{t.get('anunciantes_vistos','?')} anunciantes · {marca}")
    if cli:
        c = cli[0]
        vazios = [p for p, n in (("Meta", c.get("meta_ativos")),
                                 ("Google", c.get("google_ativos"))) if not n]
        if vazios:
            out.append(f"\n>> {c['nome']} não tem anúncio ativo em: {', '.join(vazios)}")
    return "\n".join(out)


# --------------------------------------------------------------------------
# HTML — a seção que entra no relatório do cliente
# --------------------------------------------------------------------------

def _bar(nome, val, maxv, rot, cls=""):
    w = 0 if not maxv else max(2, round(val / maxv * 100))
    return (f'<div class="row"><div class="name">{html.escape(nome)}</div>'
            f'<div class="track"><div class="fill {cls}" style="width:{w}%"></div></div>'
            f'<div class="val">{html.escape(rot)}</div></div>')


def secao_html(linhas, termos, recorte, hoje):
    p = ['<h2>Anúncios: o que o mercado está comprando</h2>']
    p.append('<p>Levantado nas bibliotecas públicas da Meta e do Google — todo anúncio ativo '
             'de qualquer anunciante é público. <b>Contagem de anúncios não é verba:</b> '
             'as bibliotecas não expõem investimento. O que ela mede é presença e '
             'maturidade de operação.</p>')

    ordenado = sorted(linhas.values(),
                      key=lambda v: -((v.get("meta_ativos") or 0) + (v.get("google_ativos") or 0)))

    p.append('<div class="scroll"><table><thead><tr><th>Marca</th>'
             '<th class="num">Meta</th><th class="num">Google</th>'
             '<th>Ângulo dominante</th><th class="num">Anúncio mais antigo</th>'
             '</tr></thead><tbody>')
    for v in ordenado:
        ang = max(v.get("angulos") or {}, key=(v.get("angulos") or {}).get, default="—")
        cls = ' class="me"' if v.get("papel") == "cliente" else ''
        antigo = v.get("meta_mais_antigo")
        p.append(f'<tr{cls}><td>{html.escape(v["nome"])}</td>'
                 f'<td class="num">{v.get("meta_ativos", "—")}</td>'
                 f'<td class="num">{v.get("google_ativos", "—")}</td>'
                 f'<td>{html.escape(ang)}</td>'
                 f'<td class="num">{(str(antigo) + " dias") if antigo else "—"}</td></tr>')
    p.append('</tbody></table></div>')
    if recorte:
        p.append(f'<p style="font-size:13px;color:var(--muted)">Recorte do Google: '
                 f'<b>{html.escape(recorte)}</b>. “Anunciante” e “domínio” medem coisas '
                 'diferentes para a mesma empresa — todos os números desta tabela usam o mesmo.</p>')

    maxv = max([(v.get("meta_ativos") or 0) + (v.get("google_ativos") or 0) for v in ordenado] or [1])
    p.append('<div class="corr"><div class="title">Presença em mídia paga</div>'
             '<div class="sub">Anúncios ativos somando as duas bibliotecas. Presença, não verba.</div>')
    for v in ordenado:
        tot = (v.get("meta_ativos") or 0) + (v.get("google_ativos") or 0)
        det = f'{v.get("meta_ativos") or 0} Meta · {v.get("google_ativos") or 0} Google'
        p.append(_bar(v["nome"], tot, maxv, det,
                      "bad" if v.get("papel") == "cliente" else "dim"))
    p.append('</div>')

    for t in termos:
        pres = t.get("cliente_presente")
        p.append('<div class="finding ' + ("good" if pres else "bad") + '">'
                 f'<h3>“{html.escape(t["termo"])}” — {t["ativos"]} anúncios ativos</h3>'
                 f'<div class="evidence">{t.get("anunciantes_vistos", "vários")} anunciantes '
                 'disputam esse termo agora na Meta. '
                 + ("O cliente está entre eles." if pres else
                    "<b>O cliente não está entre eles.</b>")
                 + " " + html.escape(t.get("nota", "")) + '</div></div>')

    # os criativos mais antigos do nicho — o que está pagando as contas
    todos = []
    for v in linhas.values():
        for a in v.get("ads") or []:
            d = dias_no_ar(a, hoje)
            if d is not None:
                todos.append((d, v["nome"], a))
    todos.sort(key=lambda x: -x[0])
    if todos:
        p.append('<h3>O que está no ar há mais tempo</h3>')
        p.append('<p>Ninguém mantém anúncio ruim rodando. Os criativos mais antigos do nicho são '
                 'o melhor palpite disponível sobre o que converte.</p><ol class="actions">')
        for d, nome, a in todos[:5]:
            copy = html.escape((a.get("copy") or "")[:220])
            p.append(f'<li><div class="what">{html.escape(nome)} — {d} dias no ar'
                     + (f' · ângulo {html.escape(a["angulo"])}' if a.get("angulo") else '')
                     + '</div>'
                     f'<div class="why">“{copy}”</div>'
                     + (f'<div class="how">Clique vai para: {html.escape(a["destino"])}</div>'
                        if a.get("destino") else '') + '</li>')
        p.append('</ol>')

    p.append('<p style="font-size:13px;color:var(--muted)">Criativo de concorrente aqui é '
             '<b>estudo</b>: entra no relatório como referência e não vai para o feed nem para o '
             'site do cliente. As bibliotecas não expõem investimento, impressões ou resultado — '
             'nenhum número desta seção deve ser lido como verba.</p>')
    return "\n".join(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo", type=Path)
    ap.add_argument("--html", type=Path, help="grava a seção HTML neste caminho")
    ap.add_argument("--resumo", action="store_true")
    ap.add_argument("--hoje", help="AAAA-MM-DD (padrão: hoje)")
    a = ap.parse_args()

    hoje = date.fromisoformat(a.hoje) if a.hoje else date.today()
    d, meta, goog, termos, recorte = carregar(a.arquivo)
    if not meta and not goog:
        sys.exit("erro: nenhum anunciante no arquivo — a coleta não rodou.")
    linhas = consolidar(meta, goog, hoje)

    if a.html:
        a.html.write_text(secao_html(linhas, termos, recorte, hoje), encoding="utf-8")
        print(f"seção: {a.html} ({len(linhas)} marcas)")
    if a.resumo or not a.html:
        print(resumo(linhas, termos, recorte))


if __name__ == "__main__":
    main()
