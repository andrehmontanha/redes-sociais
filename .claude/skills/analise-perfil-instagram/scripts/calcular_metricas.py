#!/usr/bin/env python3
"""Calcula as métricas de um perfil do Instagram a partir do JSON de coleta.

Uso:
    python calcular_metricas.py dados_<handle>.json [--nicho <nicho>] [--json]
    python calcular_metricas.py --listar-nichos

Sem --json, imprime um resumo legível. Com --json, devolve a estrutura completa
para você reaproveitar no relatório.

Três decisões embutidas aqui, todas com o mesmo motivo — não produzir número
bonito e errado:

1. `null` é "não coletado" e sai dos cálculos; nunca vira zero.
2. Posts em collab hospedados em contas de terceiros entram na contagem da grade
   mas ficam fora da taxa de engajamento: vivem numa base de seguidores
   diferente, e dividi-los pelos seguidores do cliente não significa nada.
3. O benchmark é calibrado pelo nicho. 1,2% é fraco em gastronomia e ótimo em
   B2B industrial; comparar tudo com a mesma régua produz veredito errado.
"""

import argparse
import json
import statistics
import sys
from datetime import date
from collections import defaultdict

FAIXAS = [
    (1_000, "menos de 1.000", 3.0, 8.0),
    (10_000, "1.000 a 10.000", 2.0, 5.0),
    (50_000, "10.000 a 50.000", 1.5, 3.5),
    (200_000, "50.000 a 200.000", 1.0, 2.5),
    (1_000_000, "200.000 a 1M", 0.8, 2.0),
    (float("inf"), "acima de 1M", 0.5, 1.5),
]

# Multiplicador aplicado aos pisos da faixa. Setores em que as pessoas interagem
# por prazer ficam acima de 1; setores de decisão racional e ciclo longo, abaixo.
NICHOS = {
    "humor_entretenimento": 1.5,
    "pet": 1.4,
    "moda_beleza": 1.3,
    "fitness": 1.3,
    "gastronomia": 1.3,
    "turismo_hotelaria": 1.2,
    "varejo_ecommerce": 1.0,
    "educacao": 1.0,
    "casa_decoracao": 1.0,
    "servicos_locais": 1.0,
    "saude_clinico": 0.8,
    "imobiliario": 0.7,
    "tecnologia": 0.7,
    "financeiro": 0.6,
    "juridico": 0.6,
    "b2b_industrial": 0.5,
    "generico": 1.0,
}


def faixa_de(seguidores, nicho="generico"):
    mult = NICHOS.get(nicho, 1.0)
    for limite, nome, baixo, alto in FAIXAS:
        if seguidores < limite:
            return {
                "faixa": nome,
                "nicho": nicho,
                "multiplicador_nicho": mult,
                "piso_saudavel": round(baixo * mult, 2),
                "piso_forte": round(alto * mult, 2),
                "piso_saudavel_generico": baixo,
            }
    return {"faixa": "desconhecida", "nicho": nicho, "multiplicador_nicho": mult,
            "piso_saudavel": None, "piso_forte": None, "piso_saudavel_generico": None}


def classificar(er, faixa):
    if er is None or faixa["piso_saudavel"] is None:
        return "não avaliado"
    if er >= faixa["piso_forte"]:
        return "forte"
    if er >= faixa["piso_saudavel"]:
        return "saudável"
    return "abaixo do benchmark"


def med(valores):
    valores = [v for v in valores if v is not None]
    if not valores:
        return None
    return round(statistics.mean(valores), 2)


def mediana(valores):
    valores = [v for v in valores if v is not None]
    if not valores:
        return None
    return round(statistics.median(valores), 2)


def calcular(dados, nicho=None, hoje=None):
    hoje = hoje or date.today()
    perfil = dados.get("perfil", {})
    todos = dados.get("posts", []) or []
    seguidores = perfil.get("seguidores")
    nicho = nicho or dados.get("nicho") or "generico"

    if not seguidores:
        sys.exit("erro: perfil.seguidores ausente — sem ele não há taxa de engajamento.")
    if not todos:
        sys.exit("erro: nenhum post na amostra.")

    # Um post sem o campo `autor_proprio` é tratado como próprio: coletas antigas
    # não tinham a distinção, e assumir o contrário esvaziaria a amostra em
    # silêncio — pior erro possível aqui.
    posts = [p for p in todos if p.get("autor_proprio", True)]
    collabs = [p for p in todos if not p.get("autor_proprio", True)]

    if not posts:
        sys.exit(
            "erro: nenhum post próprio na amostra — toda a grade recente é collab.\n"
            "Isso é um achado, não um bug: relate no relatório e amplie a janela de coleta."
        )

    curtidas_ocultas = all(p.get("curtidas") is None for p in posts)

    enriquecidos = []
    for p in posts:
        curtidas = p.get("curtidas")
        comentarios = p.get("comentarios")
        # ER só existe quando os dois componentes foram coletados. Somar um post
        # de curtidas ocultas como se tivesse zero curtidas puxaria a média para
        # baixo e faria o perfil parecer pior do que é.
        interacoes = None
        er = None
        if curtidas is not None and comentarios is not None:
            interacoes = curtidas + comentarios
            er = round(interacoes / seguidores * 100, 3)
        taxa_coment = (
            round(comentarios / seguidores * 100, 3) if comentarios is not None else None
        )
        cl = (
            round(comentarios / curtidas * 100, 2)
            if comentarios is not None and curtidas
            else None
        )
        views = p.get("visualizacoes")
        taxa_view = round(views / seguidores * 100, 1) if views else None
        enriquecidos.append(
            {
                **p,
                "interacoes": interacoes,
                "er": er,
                "taxa_comentarios": taxa_coment,
                "comentario_por_curtida": cl,
                "taxa_visualizacao": taxa_view,
            }
        )

    ers = [p["er"] for p in enriquecidos]
    er_medio, er_mediano = med(ers), mediana(ers)

    # Cadência
    datas = sorted(
        date.fromisoformat(p["data"]) for p in posts if p.get("data")
    )
    # A cadência tem que enxergar o silêncio até hoje.
    #
    # Sem isso, uma conta que publicou duas vezes em julho e sumiu aparece com
    # "7 posts/semana" — porque os dois posts estão a 2 dias um do outro e a
    # janela da amostra ignora os 38 dias seguintes. É o pior tipo de erro que
    # este script pode cometer: um número bonito que descreve uma conta parada
    # como se fosse a mais ativa da carteira.
    cadencia = maior_intervalo = periodo_dias = None
    dias_desde_ultimo = None
    if datas:
        dias_desde_ultimo = (hoje - datas[-1]).days
    if len(datas) >= 2:
        periodo_dias = (datas[-1] - datas[0]).days
        maior_intervalo = max(
            (datas[i + 1] - datas[i]).days for i in range(len(datas) - 1)
        )
        # o silêncio final conta como intervalo — ele é real
        if dias_desde_ultimo is not None:
            maior_intervalo = max(maior_intervalo, dias_desde_ultimo)
        janela = (periodo_dias or 0) + (dias_desde_ultimo or 0)
        if janela > 0:
            cadencia = round(len(datas) / janela * 7, 1)
    elif len(datas) == 1 and dias_desde_ultimo:
        maior_intervalo = dias_desde_ultimo
        cadencia = round(1 / max(dias_desde_ultimo, 1) * 7, 1)

    # Quando o perfil esconde curtidas, o ER não existe para ninguém de fora.
    # Em vez de devolver tudo vazio, comparamos os posts pela taxa de comentários
    # — que não é ER e não deve ser apresentada como tal, mas ordena o conteúdo
    # tão bem quanto para achar o que funciona.
    metrica = "taxa_comentarios" if curtidas_ocultas else "er"
    rotulo_metrica = "taxa de comentários" if curtidas_ocultas else "ER"

    # Por formato e por pilar/tema
    def agrupar(chave):
        grupos = defaultdict(list)
        for p in enriquecidos:
            valor = p.get(chave)
            if valor:
                grupos[valor].append(p)
        return {
            nome: {
                "posts": len(itens),
                "percentual": round(len(itens) / len(enriquecidos) * 100),
                "metrica": rotulo_metrica,
                "mediana": mediana([i[metrica] for i in itens]),
            }
            for nome, itens in sorted(
                grupos.items(), key=lambda kv: -len(kv[1])
            )
        }

    por_formato = agrupar("formato")
    por_tema = agrupar("tema")

    com_er = [p for p in enriquecidos if p["er"] is not None]
    comparaveis = [p for p in enriquecidos if p[metrica] is not None]
    ranking = sorted(comparaveis, key=lambda p: p[metrica], reverse=True)

    faixa = faixa_de(seguidores, nicho)
    # Com amostra pequena a mediana resiste melhor a um viral isolado.
    usar_mediana = len(com_er) < 12
    referencia = er_mediano if usar_mediana else er_medio

    # Sinais de possível engajamento artificial.
    #
    # Os dois primeiros só fazem sentido com base e amostra grandes o bastante
    # para existir padrão. Numa conta de 31 seguidores, "5 curtidas e nenhum
    # comentário" é o retrato normal de uma conta nova — acusar engajamento
    # comprado a partir disso é destruir a confiança do cliente em cima de ruído.
    sinais = []
    cls = [p["comentario_por_curtida"] for p in enriquecidos]
    cl_medio = med(cls)
    base_pequena = seguidores < 1000 or len(com_er) < 5
    if base_pequena:
        sinais.append(
            f"detecção de engajamento artificial desligada — {seguidores} seguidores e "
            f"{len(com_er)} posts na amostra são pouco para separar padrão de ruído"
        )

    if not base_pequena and cl_medio is not None and cl_medio < 0.3:
        sinais.append(
            f"proporção comentário/curtida muito baixa ({cl_medio}%) — abaixo de 0,3% é atípico"
        )
    if (not base_pequena and referencia and faixa["piso_forte"]
            and referencia > faixa["piso_forte"] * 2):
        sinais.append(
            f"ER de {referencia}% está muito acima do teto da faixa ({faixa['piso_forte']}%) — vale conferir a qualidade dos comentários"
        )
    # Este não depende de tamanho de base: descreve a forma da distribuição.
    if er_medio and er_mediano and er_mediano > 0 and er_medio > er_mediano * 1.8:
        sinais.append(
            "média muito acima da mediana — o resultado depende de 1–2 posts virais, não de consistência"
        )

    return {
        "handle": dados.get("handle"),
        "coletado_em": dados.get("coletado_em"),
        "seguidores": seguidores,
        "amostra": {
            "posts_proprios": len(posts),
            "collabs_na_grade": len(collabs),
            "share_da_grade_terceirizado": (
                round(len(collabs) / len(todos) * 100) if todos else 0
            ),
            "posts_com_engajamento_completo": len(com_er),
            "periodo_dias": periodo_dias,
            "robustez": "indicativa" if len(com_er) < 9 else "adequada",
            "curtidas_ocultas": curtidas_ocultas,
        },
        "collabs": {
            "anfitrioes": sorted({p.get("anfitriao") for p in collabs if p.get("anfitriao")}),
            "curtidas_totais": sum(p.get("curtidas") or 0 for p in collabs),
            "comentarios_totais": sum(p.get("comentarios") or 0 for p in collabs),
            "nota": (
                "Números absolutos apenas. Estes posts vivem em contas com outra base "
                "de seguidores — calcular ER sobre os seguidores do cliente daria um "
                "número sem significado."
            ),
        },
        "engajamento": {
            "metrica_comparativa": rotulo_metrica,
            "er_medio": er_medio,
            "er_mediano": er_mediano,
            "metrica_de_referencia": "mediana" if usar_mediana else "média",
            "valor_de_referencia": referencia,
            "classificacao": (
                "não avaliado — curtidas ocultas, use a taxa de comentários"
                if curtidas_ocultas
                else "não avaliável — base pequena demais para taxa significar algo"
                if base_pequena
                else classificar(referencia, faixa)
            ),
            "benchmark": faixa,
            "comentario_por_curtida_medio": cl_medio,
            "taxa_comentarios_mediana": mediana(
                [p["taxa_comentarios"] for p in enriquecidos]
            ),
            "taxa_comentarios_referencia": "0,05% a 0,2% é a faixa comum",
        },
        "cadencia": {
            "posts_por_semana": cadencia,
            "dias_desde_o_ultimo_post": dias_desde_ultimo,
            "parado": bool(dias_desde_ultimo and dias_desde_ultimo > 21),
            "maior_intervalo_dias": maior_intervalo,
        },
        "por_formato": por_formato,
        "por_tema": por_tema,
        "melhores_posts": [
            {
                k: p.get(k)
                for k in (
                    "url", "data", "formato", "tema", "er",
                    "taxa_comentarios", "taxa_visualizacao",
                )
            }
            for p in ranking[:3]
        ],
        "piores_posts": [
            {
                k: p.get(k)
                for k in ("url", "data", "formato", "tema", "er", "taxa_comentarios")
            }
            for p in ranking[-3:]
        ],
        "sinais_de_alerta": sinais,
        "posts": enriquecidos,
    }


def imprimir(r):
    eng, am = r["engajamento"], r["amostra"]
    print(f"\n=== @{r['handle']} — coletado em {r['coletado_em']} ===")
    print(f"Seguidores: {r['seguidores']:,}".replace(",", "."))
    print(
        f"Amostra: {am['posts_proprios']} posts próprios / {am['periodo_dias']} dias "
        f"({am['robustez']})"
        + (
            f" · {am['posts_com_engajamento_completo']} com curtidas e comentários"
            if am["posts_com_engajamento_completo"] != am["posts_proprios"]
            else ""
        )
    )
    if am["collabs_na_grade"]:
        c = r["collabs"]
        print(
            f"Collabs na grade: {am['collabs_na_grade']} "
            f"({am['share_da_grade_terceirizado']}% dos itens recentes) — "
            f"{c['curtidas_totais']} curtidas e {c['comentarios_totais']} comentários,"
            " fora do cálculo de ER"
        )
        if c["anfitrioes"]:
            print(f"  hospedados em: {', '.join('@' + a for a in c['anfitrioes'])}")
    if am["curtidas_ocultas"]:
        print("!! curtidas ocultas — use a taxa de comentários como referência")

    def pct(v):
        return "n/d" if v is None else f"{v}%"

    metrica = eng["metrica_comparativa"]

    print("\n-- Engajamento --")
    print(f"ER médio:   {pct(eng['er_medio'])}")
    print(f"ER mediano: {pct(eng['er_mediano'])}")
    print(
        f"Referência ({eng['metrica_de_referencia']}): {pct(eng['valor_de_referencia'])} "
        f"→ {eng['classificacao']}"
    )
    b = eng["benchmark"]
    print(
        f"Benchmark {b['faixa']} · nicho {b['nicho']} (×{b['multiplicador_nicho']}): "
        f"saudável a partir de {b['piso_saudavel']}%, forte a partir de {b['piso_forte']}%"
    )
    print(f"Comentário/curtida: {pct(eng['comentario_por_curtida_medio'])}")
    print(
        f"Taxa de comentários (mediana): {pct(eng['taxa_comentarios_mediana'])} "
        f"— {eng['taxa_comentarios_referencia']}"
    )

    c = r["cadencia"]
    print("\n-- Cadência --")
    print(f"{c['posts_por_semana']} posts/semana · maior intervalo: {c['maior_intervalo_dias']} dias"
          + (f" · SEM PUBLICAR HÁ {c['dias_desde_o_ultimo_post']} DIAS"
             if c.get("parado") else ""))

    for titulo, grupo in (("Formato", r["por_formato"]), ("Tema", r["por_tema"])):
        if grupo:
            print(f"\n-- Por {titulo.lower()} (mediana de {metrica}) --")
            for nome, v in grupo.items():
                print(f"{nome:<28} {v['percentual']:>3}% dos posts · {pct(v['mediana'])}")

    print(f"\n-- Melhores posts (por {metrica}) --")
    for p in r["melhores_posts"]:
        valor = p["er"] if metrica == "ER" else p["taxa_comentarios"]
        print(f"{pct(valor):>9}  {p['data']}  {p['formato']:<10} {p.get('tema') or ''}")

    if r["sinais_de_alerta"]:
        print("\n-- Sinais para investigar --")
        for s in r["sinais_de_alerta"]:
            print(f"* {s}")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("arquivo", nargs="?")
    ap.add_argument("--nicho", help="calibra o benchmark; ver --listar-nichos")
    ap.add_argument("--listar-nichos", action="store_true")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    args = ap.parse_args()

    if args.listar_nichos:
        linhas = ["Nichos e multiplicador aplicado ao benchmark da faixa:", ""]
        linhas += [f"  {n:<24} ×{m}" for n, m in sorted(NICHOS.items(), key=lambda kv: -kv[1])]
        linhas += ["", "Se o nicho do cliente não estiver aqui, escolha o mais próximo em "
                   "lógica de consumo — o que importa é se as pessoas interagem por "
                   "prazer ou por decisão racional."]
        try:
            print("\n".join(linhas))
        except BrokenPipeError:  # saída canalizada para head/less
            pass
        return

    if not args.arquivo:
        ap.error("informe o arquivo de dados ou use --listar-nichos")

    with open(args.arquivo, encoding="utf-8") as f:
        dados = json.load(f)

    if args.nicho and args.nicho not in NICHOS:
        print(f"aviso: nicho '{args.nicho}' desconhecido, usando multiplicador 1.0 "
              f"(veja --listar-nichos)", file=sys.stderr)

    resultado = calcular(dados, args.nicho)
    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        imprimir(resultado)


if __name__ == "__main__":
    main()
