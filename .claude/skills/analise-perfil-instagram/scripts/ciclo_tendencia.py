#!/usr/bin/env python3
"""Estágio, janela restante e aderência de cada tendência coletada.

Uso:
    python ciclo_tendencia.py tendencias_<handle>.json [--json]

A conta é simples de propósito: duração típica da categoria, menos o tempo que a
trend já viveu, ajustada por crescimento, pico e saturação no nicho. O valor não
é uma previsão — é uma estimativa defensável de prazo de produção. Apresente-a
sempre como projeção, nunca como certeza.

Entrada esperada (campos ausentes são tratados como desconhecidos):

{
  "handle": "exemplo",
  "avaliado_em": "2026-08-26",
  "apetite": "equilibrado",              // conservador | equilibrado | agressivo
  "tendencias": [{
    "nome": "Áudio tal",
    "tipo": "audio",                     // audio|meme|evento|challenge|formato|estetica|sazonal
    "camada": "geral",                   // nicho | geral | ambas
    "primeira_aparicao": "2026-08-18",
    "volume_atual": 45000,
    "volume_anterior": 20000,
    "melhores_reels_dias": 2,            // idade dos Reels que melhor performam com ela
    "perfis_nicho_usando": 1,
    "data_alvo": null,                   // só para tipo "sazonal"
    "aderencia": {"produto": 3, "pilar": 2, "viabilidade": 2, "seguranca": 1}
  }]
}
"""

import argparse
import json
import sys
from datetime import date

# Duração útil típica em dias e dia em que o pico costuma cair.
# Fonte: padrões observados de ciclo de trend; ajuste conforme sua própria série.
CATEGORIAS = {
    "audio":     {"duracao": 15,  "pico": 10, "rotulo": "áudio viral"},
    "meme":      {"duracao": 10,  "pico": 6,  "rotulo": "meme / trecho de fala"},
    "evento":    {"duracao": 6,   "pico": 3,  "rotulo": "pauta de evento"},
    "challenge": {"duracao": 21,  "pico": 14, "rotulo": "challenge / coreografia"},
    "formato":   {"duracao": 56,  "pico": 28, "rotulo": "formato de Reel"},
    "estetica":  {"duracao": 135, "pico": 60, "rotulo": "estética visual"},
    "sazonal":   {"duracao": None, "pico": None, "rotulo": "sazonal"},
}

CORTE_APETITE = {"conservador": 8, "equilibrado": 6, "agressivo": 4}


def dias_entre(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def nota_aderencia(ad):
    """Soma a rubrica. Segurança de marca zero elimina, por mais alto que seja o resto."""
    if not ad:
        return None, None
    total = (
        min(ad.get("produto", 0), 4)
        + min(ad.get("pilar", 0), 3)
        + min(ad.get("viabilidade", 0), 2)
        + min(ad.get("seguranca", 0), 1)
    )
    vetado = ad.get("seguranca", 0) == 0
    return total, vetado


def avaliar(t, hoje):
    tipo = t.get("tipo", "formato")
    cat = CATEGORIAS.get(tipo, CATEGORIAS["formato"])
    nome = t.get("nome", "(sem nome)")

    nicho_usando = t.get("perfis_nicho_usando")
    melhores_dias = t.get("melhores_reels_dias")
    v_atual, v_ant = t.get("volume_atual"), t.get("volume_anterior")

    crescendo = None
    if v_atual is not None and v_ant:
        crescendo = v_atual > v_ant * 1.15

    # --- Sazonal tem relógio próprio: a data manda, não a curva de uso. ---
    if tipo == "sazonal" and t.get("data_alvo"):
        faltam = dias_entre(hoje, t["data_alvo"])
        if faltam < 0:
            estagio, janela = "saindo", 0
        elif faltam > 21:
            estagio, janela = "emergente", faltam - 10
        elif faltam >= 7:
            estagio, janela = "no pico", faltam
        else:
            estagio, janela = "saturando", faltam
        return montar(t, nome, cat, estagio, janela, crescendo, nicho_usando,
                      obs=f"faltam {faltam} dias para a data")

    # --- Demais categorias: duração típica menos idade, ajustada por sinais. ---
    idade = None
    if t.get("primeira_aparicao"):
        idade = dias_entre(t["primeira_aparicao"], hoje)

    if idade is None:
        return montar(t, nome, cat, "indeterminado", None, crescendo, nicho_usando,
                      obs="sem data de primeira aparição — janela não estimável")

    janela = cat["duracao"] - idade
    ajustes = []

    if crescendo or (melhores_dias is not None and melhores_dias <= 3):
        janela *= 1.3
        ajustes.append("ainda crescendo (+30%)")
    if melhores_dias is not None and melhores_dias > 10:
        janela *= 0.5
        ajustes.append("passou do pico (−50%)")
    if nicho_usando is not None and nicho_usando >= 3:
        janela *= 0.5
        ajustes.append("saturada no nicho (−50%)")

    janela = max(int(round(janela)), 0)

    # Estágio: combina posição na curva geral com adoção pelo nicho.
    if janela <= 0:
        estagio = "saindo"
    elif nicho_usando is not None and nicho_usando >= 3:
        estagio = "saturando"
    elif idade <= cat["pico"] and (nicho_usando is None or nicho_usando <= 1):
        estagio = "emergente"
    elif idade <= cat["pico"]:
        estagio = "no pico"
    else:
        estagio = "saturando"

    # Uma trend madura no Instagram em geral que o nicho ainda não adotou não está
    # saturada PARA ESTA MARCA — é justamente a oportunidade que o módulo procura.
    # Sem esta correção, o melhor encaixe da lista sai rotulado como "condicional".
    if (
        estagio == "saturando"
        and nicho_usando is not None
        and nicho_usando <= 1
        and janela > 0
    ):
        estagio = "no pico"
        ajustes.append("madura no geral, mas o nicho ainda não adotou")
        obs_extra = True
    else:
        obs_extra = False

    obs = "; ".join(ajustes) if ajustes else "sem ajustes"
    av = montar(t, nome, cat, estagio, janela, crescendo, nicho_usando,
                obs=obs, idade=idade)
    av["virgem_no_nicho"] = obs_extra
    return av


def montar(t, nome, cat, estagio, janela, crescendo, nicho_usando, obs, idade=None):
    nota, vetado = nota_aderencia(t.get("aderencia"))
    return {
        "nome": nome,
        "tipo": cat["rotulo"],
        "camada": t.get("camada"),
        "estagio": estagio,
        "idade_dias": idade,
        "janela_restante_dias": janela,
        "crescendo": crescendo,
        "perfis_nicho_usando": nicho_usando,
        "aderencia": nota,
        "vetado_por_seguranca": vetado,
        "ajustes": obs,
    }


def decidir(av, corte):
    if av["aderencia"] is None:
        return "avaliar", "aderência não pontuada"
    if av["vetado_por_seguranca"]:
        return "descartar", "risco de marca — alcance não compensa dano de posicionamento"
    if av["estagio"] == "saindo":
        return "descartar", "janela fechada; guarde como aprendizado de formato"
    if av["aderencia"] < corte:
        return "descartar", f"aderência {av['aderencia']} abaixo do corte {corte}"
    if av["estagio"] == "saturando":
        return "condicional", "só com um ângulo genuinamente diferente do que o nicho já fez"
    if av.get("virgem_no_nicho"):
        return "entrar", "madura no Instagram em geral, mas ninguém do nicho usa — é a vantagem da lista"
    if av["janela_restante_dias"] is not None and av["janela_restante_dias"] <= 4:
        return "urgente", "produzir em até 48h ou deixar passar"
    return "entrar", "janela aberta e aderência suficiente"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("arquivo")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    with open(args.arquivo, encoding="utf-8") as f:
        dados = json.load(f)

    hoje = dados.get("avaliado_em") or date.today().isoformat()
    apetite = (dados.get("apetite") or "equilibrado").lower()
    corte = CORTE_APETITE.get(apetite, 6)

    tends = dados.get("tendencias") or []
    if not tends:
        sys.exit("erro: nenhuma tendência na entrada.")

    saida = []
    for t in tends:
        av = avaliar(t, hoje)
        av["decisao"], av["motivo"] = decidir(av, corte)
        saida.append(av)

    ordem = {"urgente": 0, "entrar": 1, "condicional": 2, "avaliar": 3, "descartar": 4}
    saida.sort(key=lambda a: (ordem[a["decisao"]], -(a["aderencia"] or 0),
                              a["janela_restante_dias"] if a["janela_restante_dias"] is not None else 999))

    resultado = {
        "handle": dados.get("handle"),
        "avaliado_em": hoje,
        "apetite": apetite,
        "corte_de_aderencia": corte,
        "tendencias": saida,
    }

    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return

    print(f"\n=== Tendências — @{resultado['handle']} · {hoje} ===")
    print(f"Apetite: {apetite} (corte de aderência: {corte}/10)\n")
    cab = f"{'DECISÃO':<12}{'ADER':<6}{'ESTÁGIO':<13}{'JANELA':<9}{'CAMADA':<9}TENDÊNCIA"
    print(cab)
    print("-" * max(len(cab), 76))
    for a in saida:
        janela = "n/d" if a["janela_restante_dias"] is None else f"{a['janela_restante_dias']}d"
        nota = "n/d" if a["aderencia"] is None else f"{a['aderencia']}/10"
        print(f"{a['decisao']:<12}{nota:<6}{a['estagio']:<13}{janela:<9}"
              f"{(a['camada'] or '-'):<9}{a['nome']}")
        print(f"{'':<12}↳ {a['motivo']} · {a['tipo']} · {a['ajustes']}")
    print()


if __name__ == "__main__":
    main()
