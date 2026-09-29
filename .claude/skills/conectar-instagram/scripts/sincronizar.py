#!/usr/bin/env python3
"""Lê a conta conectada de um cliente — perfil, posts, legendas, mídia original e
métricas internas — e grava tudo na pasta do cliente, no formato que a análise usa.

Uso:
    python sincronizar.py --cliente <handle> [--limite 60] [--sem-midia] [--fuso America/Sao_Paulo] [--nicho turismo_hotelaria]
    python sincronizar.py --cliente <handle> --de-arquivo resposta.json   # offline (testes / reprocessar)

Grava em clientes/<handle>/:
    instagram/AAAA-MM-DD/perfil.json        dados do perfil
    instagram/AAAA-MM-DD/midias.json        cada post com legenda, datas e métricas internas
    instagram/AAAA-MM-DD/conta-insights.json alcance/views/interações da conta (30 dias), se disponível
    instagram/AAAA-MM-DD/dados_<handle>.json formato do calcular_metricas.py (análise)
    instagram/AAAA-MM-DD/resumo.md          o que funciona: tops, formatos, horários, legendas
    instagram/AAAA-MM-DD/bruto.json         resposta crua (para reprocessar com --de-arquivo)
    referencias/cliente/ig-<shortcode>[-N].jpg      imagens originais (1080 px)
    referencias/cliente/videos/ig-<shortcode>.mp4   vídeos originais + capa .jpg

Métricas internas (só o dono vê): alcance, salvamentos, compartilhamentos,
visualizações, interações totais. Com elas o resumo ranqueia por ALCANCE e por
SALVAMENTO/ALCANCE — não por curtida, que é a métrica mais fácil de inflar e a que
menos prevê resultado.
"""

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ig_api  # noqa: E402

CAMPOS_MIDIA = ("id,caption,media_type,media_product_type,media_url,thumbnail_url,permalink,shortcode,"
                "timestamp,like_count,comments_count,children{id,media_type,media_url,thumbnail_url}")
METRICAS = {"REELS": "reach,saved,shares,views,total_interactions,likes,comments",
            "FEED": "reach,saved,shares,views,total_interactions,likes,comments",
            "STORY": "reach,views,shares,total_interactions"}
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


# ---------------------------------------------------------------- coleta

def coletar_api(handle, limite):
    conta = ig_api.Conta(handle)
    perfil = conta.get(conta.user_id, fields="user_id,username,name,biography,website,followers_count,"
                                              "follows_count,media_count,profile_picture_url,account_type")
    midias, insights, falhas = [], {}, 0
    for m in conta.paginas(f"{conta.user_id}/media", limite=limite, fields=CAMPOS_MIDIA, limit=50):
        midias.append(m)
        tipo = m.get("media_product_type", "FEED")
        try:
            d = conta.get(f"{m['id']}/insights", metric=METRICAS.get(tipo, METRICAS["FEED"]))
            insights[m["id"]] = {x["name"]: valor(x) for x in d.get("data", [])}
        except RuntimeError:
            falhas += 1  # post anterior à conversão para conta profissional, ou métrica indisponível
    conta_ins = {}
    fim = datetime.now(timezone.utc)
    try:
        d = conta.get(f"{conta.user_id}/insights", metric="reach,views,accounts_engaged,total_interactions",
                      period="day", metric_type="total_value",
                      since=int((fim - timedelta(days=30)).timestamp()), until=int(fim.timestamp()))
        conta_ins = {x["name"]: valor(x) for x in d.get("data", [])}
    except RuntimeError as e:
        conta_ins = {"erro": str(e)}
    if falhas:
        print(f"! {falhas} post(s) sem insights (anteriores à conta profissional ou métrica indisponível)")
    return {"perfil": perfil, "midias": midias, "insights": insights, "conta_insights": conta_ins}, conta


def valor(metrica):
    if "total_value" in metrica:
        return metrica["total_value"].get("value")
    vals = metrica.get("values") or [{}]
    return vals[0].get("value")


# ---------------------------------------------------------------- mídia

def baixar(url, destino: Path):
    import requests
    if destino.exists():
        return True
    r = requests.get(url, timeout=120, stream=True)
    if r.status_code != 200:
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        for bloco in r.iter_content(1 << 16):
            f.write(bloco)
    return True


def baixar_midias(bruto, pasta_refs: Path):
    ok = falha = 0
    for m in bruto["midias"]:
        sc = m.get("shortcode") or m["id"]
        itens = m.get("children", {}).get("data") or [m]
        for i, it in enumerate(itens, 1):
            suf = f"-{i}" if len(itens) > 1 else ""
            if it.get("media_type") == "VIDEO":
                pares = [(it.get("media_url"), pasta_refs / "videos" / f"ig-{sc}{suf}.mp4"),
                         (it.get("thumbnail_url"), pasta_refs / "videos" / f"ig-{sc}{suf}.jpg")]
            else:
                pares = [(it.get("media_url"), pasta_refs / f"ig-{sc}{suf}.jpg")]
            for url, destino in pares:
                if not url:
                    continue
                if baixar(url, destino):
                    ok += 1
                else:
                    falha += 1
    return ok, falha


# ---------------------------------------------------------------- análise

def formato(m):
    if m.get("media_product_type") == "REELS":
        return "reel"
    if m.get("media_type") == "CAROUSEL_ALBUM":
        return "carrossel"
    if m.get("media_product_type") == "STORY":
        return "story"
    return "video" if m.get("media_type") == "VIDEO" else "imagem"


def montar_posts(bruto, fuso):
    posts = []
    for m in bruto["midias"]:
        ins = bruto["insights"].get(m["id"], {})
        quando = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(fuso)
        legenda = m.get("caption") or ""
        alcance = ins.get("reach")
        posts.append({
            "id": m["id"], "url": m.get("permalink"), "shortcode": m.get("shortcode"),
            "data": quando.date().isoformat(), "hora": quando.strftime("%H:%M"), "dia_semana": DIAS[quando.weekday()],
            "formato": formato(m), "tema": None,
            "curtidas": ins.get("likes", m.get("like_count")),
            "comentarios": ins.get("comments", m.get("comments_count")),
            "visualizacoes": ins.get("views"),
            "alcance": alcance, "salvamentos": ins.get("saved"), "compartilhamentos": ins.get("shares"),
            "interacoes_totais": ins.get("total_interactions"),
            "taxa_salvamento": round(ins["saved"] / alcance * 100, 2) if alcance and ins.get("saved") is not None else None,
            "taxa_compartilhamento": round(ins["shares"] / alcance * 100, 2) if alcance and ins.get("shares") is not None else None,
            "legenda": legenda, "tamanho_legenda": len(legenda),
            "hashtags": re.findall(r"#(\w+)", legenda),
            "autor_proprio": True,
        })
    return posts


def mediana(v):
    v = [x for x in v if x is not None]
    return statistics.median(v) if v else None


def fmt(n, casas=0):
    if n is None:
        return "—"
    return f"{n:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def resumo(perfil, posts, conta_ins, handle):
    L = [f"# @{handle} — o que funciona (dados internos da conta)", "",
         f"Sincronizado em {date.today():%d/%m/%Y} · {len(posts)} posts · "
         f"{fmt(perfil.get('followers_count'))} seguidores", ""]
    com_alcance = [p for p in posts if p["alcance"]]
    if conta_ins and "erro" not in conta_ins:
        L += ["## Conta, últimos 30 dias", "",
              f"Alcance {fmt(conta_ins.get('reach'))} · Visualizações {fmt(conta_ins.get('views'))} · "
              f"Contas engajadas {fmt(conta_ins.get('accounts_engaged'))} · Interações {fmt(conta_ins.get('total_interactions'))}", ""]

    def tabela(titulo, chave, lista, casas=0, sufixo=""):
        L.extend([f"## {titulo}", "", "| # | data | formato | valor | alcance | post |", "|---|---|---|---|---|---|"])
        for i, p in enumerate(lista[:8], 1):
            L.append(f"| {i} | {p['data']} {p['hora']} | {p['formato']} | {fmt(p[chave], casas)}{sufixo} | "
                     f"{fmt(p['alcance'])} | [{(p['legenda'][:40] or p['shortcode'] or '').replace('|', ' ').replace(chr(10), ' ')}]({p['url']}) |")
        L.append("")

    if com_alcance:
        tabela("Maior alcance", "alcance", sorted(com_alcance, key=lambda p: -p["alcance"]))
        base = [p for p in com_alcance if p["taxa_salvamento"] is not None]
        tabela("Mais salvos por alcance (conteúdo que as pessoas querem guardar)", "taxa_salvamento",
               sorted(base, key=lambda p: -p["taxa_salvamento"]), 2, "%")
        base = [p for p in com_alcance if p["taxa_compartilhamento"] is not None]
        tabela("Mais compartilhados por alcance (conteúdo que leva a marca adiante)", "taxa_compartilhamento",
               sorted(base, key=lambda p: -p["taxa_compartilhamento"]), 2, "%")

        L += ["## Por formato (medianas)", "", "| formato | posts | alcance | salv./alcance | compart./alcance | views |",
              "|---|---|---|---|---|---|"]
        grupos = defaultdict(list)
        for p in com_alcance:
            grupos[p["formato"]].append(p)
        for f, g in sorted(grupos.items(), key=lambda x: -(mediana([p["alcance"] for p in x[1]]) or 0)):
            L.append(f"| {f} | {len(g)} | {fmt(mediana([p['alcance'] for p in g]))} | "
                     f"{fmt(mediana([p['taxa_salvamento'] for p in g]), 2)}% | "
                     f"{fmt(mediana([p['taxa_compartilhamento'] for p in g]), 2)}% | "
                     f"{fmt(mediana([p['visualizacoes'] for p in g]))} |")
        L.append("")

        L += ["## Quando publicar (alcance mediano por janela, mínimo 3 posts)", ""]
        janelas = defaultdict(list)
        for p in com_alcance:
            h = int(p["hora"][:2])
            bloco = "06–11h" if 6 <= h < 12 else "12–17h" if 12 <= h < 18 else "18–23h" if h >= 18 else "00–05h"
            janelas[(p["dia_semana"], bloco)].append(p["alcance"])
        validas = sorted(((mediana(v), k, len(v)) for k, v in janelas.items() if len(v) >= 3), reverse=True)
        if validas:
            for med, (dia, bloco), n in validas[:5]:
                L.append(f"- **{dia} {bloco}** — alcance mediano {fmt(med)} ({n} posts)")
        else:
            L.append("- amostra pequena demais por janela; publique em horários variados para aprender")
        L.append("")

        L += ["## Legendas", ""]
        curtas = [p["alcance"] for p in com_alcance if p["tamanho_legenda"] < 300]
        longas = [p["alcance"] for p in com_alcance if p["tamanho_legenda"] >= 300]
        L.append(f"- até 300 caracteres: alcance mediano {fmt(mediana(curtas))} ({len(curtas)} posts) · "
                 f"acima: {fmt(mediana(longas))} ({len(longas)} posts)")
        tags = Counter(t.lower() for p in posts for t in p["hashtags"])
        if tags:
            L.append("- hashtags mais usadas: " + ", ".join(f"#{t} ({n})" for t, n in tags.most_common(12)))
        L.append("")
    else:
        L += ["Sem métricas internas nesta sincronização — confira se a permissão "
              "`instagram_business_manage_insights` foi concedida.", ""]

    datas = sorted(date.fromisoformat(p["data"]) for p in posts)
    if len(datas) >= 2:
        semanas = max(1, (datas[-1] - datas[0]).days / 7)
        L += ["## Cadência", "", f"{len(datas) / semanas:.1f} posts/semana entre {datas[0]:%d/%m/%Y} e {datas[-1]:%d/%m/%Y}", ""]
    L += ["_Alcance é estimado pela Meta. Views estão marcadas pela Meta como métrica em desenvolvimento._"]
    return "\n".join(L)


# ---------------------------------------------------------------- main

def main():
    ig_api.carregar_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--limite", type=int, default=60, help="posts mais recentes (padrão 60)")
    ap.add_argument("--sem-midia", action="store_true", help="não baixa imagens/vídeos")
    ap.add_argument("--fuso", default="America/Sao_Paulo")
    ap.add_argument("--nicho", help="nicho para o calcular_metricas.py (ex.: turismo_hotelaria)")
    ap.add_argument("--de-arquivo", type=Path, help="reprocessa uma resposta gravada (bruto.json)")
    a = ap.parse_args()

    raiz = ig_api.RAIZ / "clientes" / a.cliente
    if a.de_arquivo:
        bruto = json.loads(a.de_arquivo.read_text(encoding="utf-8"))
    else:
        bruto, _ = coletar_api(a.cliente, a.limite)
    perfil = bruto["perfil"]
    if perfil.get("username", a.cliente).lower() != a.cliente.lower():
        sys.exit(f"dados de @{perfil.get('username')}, não de @{a.cliente}")

    saida = raiz / "instagram" / date.today().isoformat()
    saida.mkdir(parents=True, exist_ok=True)
    fuso = ZoneInfo(a.fuso)
    posts = montar_posts(bruto, fuso)
    (saida / "bruto.json").write_text(json.dumps(bruto, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "perfil.json").write_text(json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "midias.json").write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "conta-insights.json").write_text(json.dumps(bruto.get("conta_insights", {}), ensure_ascii=False,
                                                          indent=2), encoding="utf-8")
    dados = {
        "handle": a.cliente, "coletado_em": date.today().isoformat(), "fonte": "api_oficial",
        "nicho": a.nicho,
        "perfil": {"seguidores": perfil.get("followers_count"), "seguindo": perfil.get("follows_count"),
                   "posts": perfil.get("media_count"), "bio": perfil.get("biography"), "site": perfil.get("website"),
                   "nome": perfil.get("name")},
        "posts": posts,
    }
    (saida / f"dados_{a.cliente}.json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "resumo.md").write_text(resumo(perfil, posts, bruto.get("conta_insights"), a.cliente), encoding="utf-8")

    midia = ""
    if not a.sem_midia and not a.de_arquivo:
        ok, falha = baixar_midias(bruto, raiz / "referencias" / "cliente")
        midia = f" · {ok} arquivo(s) baixado(s)" + (f", {falha} falha(s)" if falha else "")
    print(f"✓ @{a.cliente}: {len(posts)} posts, {sum(1 for p in posts if p['alcance'])} com métricas internas{midia}")
    print(f"  {saida}/resumo.md")


if __name__ == "__main__":
    main()
