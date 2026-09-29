#!/usr/bin/env python3
"""Gera o manifesto de uma análise e o caminho onde ela deve ser gravada.

Uso:
    # análise do cliente
    python abrir_projeto.py --handle thermasdeolimpiaresort --tipo cliente \\
        --segmento "resort e parque aquático" --oferta servicos \\
        --objetivo "venda direta" --frequencia "3x por semana" \\
        --pasta-base "C:/Users/Fulano/Documents/Analises-Instagram" --saida projeto/

    # perfil de comparação, aninhado sob o cliente
    python abrir_projeto.py --handle enjoyolimpiaparkresort --tipo comparacao \\
        --cliente thermasdeolimpiaresort --pasta-base "..." --saida projeto/

Estrutura produzida:

    <PASTA_BASE>/
    └── <handle-do-cliente>/
        ├── analise - DD-MM-AAAA/
        │   ├── dados/  assets/  entregas/
        └── perfis de comparação/
            └── <handle-do-concorrente>/
                └── analise - DD-MM-AAAA/

O @ do cliente é a raiz e nunca muda. Cada análise é uma subpasta datada — nova
análise **nunca sobrescreve** a anterior, porque é a série que permite dizer
"melhorou". Os perfis de comparação repetem a mesma convenção um nível abaixo,
para que `historico.py` consiga varrer tudo depois.
"""

import argparse
from datetime import date
from pathlib import Path


def caminho_analise(base, handle_cliente, handle, tipo, nome_analise, windows):
    sep = "\\" if windows else "/"
    partes = [base.rstrip("/\\"), handle_cliente]
    if tipo == "comparacao":
        partes += ["perfis de comparação", handle]
    partes += [nome_analise]
    return sep.join(partes)


def manifesto(ctx):
    if ctx["tipo"] == "comparacao":
        cabecalho = f"""# Perfil de comparação — @{ctx['handle']}

**Analisado em:** {ctx['hoje_br']}
**Cliente de referência:** @{ctx['cliente']}
**Papel:** perfil de comparação — serve de benchmark e referência de formato

> Material desta pasta é de terceiro. Vale para benchmark, moodboard e estudo de
> formato. **Não vai para o site nem para o feed do cliente.**
"""
    else:
        cabecalho = f"""# Análise de @{ctx['handle']}

**Analisado em:** {ctx['hoje_br']}
**Segmento:** {ctx['segmento']}
**Vende:** {ctx['oferta']}
**Objetivo principal:** {ctx['objetivo']}
**Frequência de postagem declarada:** {ctx['frequencia']}
**Nicho (calibra os benchmarks):** {ctx['nicho']}
"""

    return cabecalho + f"""
## Estrutura desta análise

```
{ctx['nome_analise']}/
├── README.md   este arquivo
├── dados/      JSON de coleta — a fonte da verdade dos números
├── assets/     material capturado (ver regras de uso abaixo)
└── entregas/   relatório .md e .html, moodboard, pacote .zip
```

## Regras de uso do material

- **`assets/cliente/`** — material do próprio cliente. Uso livre no site e no feed.
- **`assets/referencia/`** — material de terceiros. Benchmark, moodboard e estudo.
  **Nunca publicar.**
- Vídeos e arquivos baixados para estudo são insumo temporário: o que sobrevive é o
  **teardown**, não o arquivo.

## Rastreabilidade

Todo número do relatório precisa ser rastreável até um arquivo em `dados/`. Se um
dado não está lá, ele não deveria estar no relatório.

## Continuidade

Esta pasta faz parte da série de análises de **@{ctx['cliente']}**. Análises
anteriores ficam em pastas irmãs `analise - DD-MM-AAAA`, e perfis de comparação em
`perfis de comparação/`. Para consolidar a série:

```bash
python scripts/historico.py --pasta <jsons staged> --cliente {ctx['cliente']}
```

---

*Pasta criada pela skill `analise-perfil-instagram`.*
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--handle", required=True)
    ap.add_argument("--tipo", choices=["cliente", "comparacao"], default="cliente")
    ap.add_argument("--cliente", help="handle do cliente (obrigatório se tipo=comparacao)")
    ap.add_argument("--segmento", default="(a definir)")
    ap.add_argument("--oferta", default="(a definir)", help="produtos, serviços ou ambos")
    ap.add_argument("--objetivo", default="(a definir)")
    ap.add_argument("--frequencia", default="(a definir)")
    ap.add_argument("--nicho", default="(a detectar)")
    ap.add_argument("--pasta-base", default="<PASTA_BASE>")
    ap.add_argument("--saida", type=Path, default=Path("projeto"))
    a = ap.parse_args()

    handle = a.handle.lstrip("@")
    cliente = (a.cliente or handle).lstrip("@")
    if a.tipo == "comparacao" and not a.cliente:
        ap.error("--tipo comparacao exige --cliente")

    hoje = date.today()
    nome_analise = f"analise - {hoje.strftime('%d-%m-%Y')}"

    base = a.pasta_base.rstrip("/\\")
    windows = ":" in base[:3] or "\\" in base
    if windows:
        base = base.replace("/", "\\")
    sep = "\\" if windows else "/"

    ctx = {
        "handle": handle, "cliente": cliente, "tipo": a.tipo,
        "segmento": a.segmento, "oferta": a.oferta, "objetivo": a.objetivo,
        "frequencia": a.frequencia, "nicho": a.nicho,
        "hoje_br": hoje.strftime("%d/%m/%Y"), "nome_analise": nome_analise,
    }

    a.saida.mkdir(parents=True, exist_ok=True)
    readme = a.saida / "README.md"
    readme.write_text(manifesto(ctx), encoding="utf-8")

    pasta = caminho_analise(base, cliente, handle, a.tipo, nome_analise, windows)

    print(f"manifesto: {readme}")
    print(f"pasta da análise: {pasta}")
    print(f"\nGrave o README com device_commit_files em:")
    print(f"  {pasta}{sep}README.md")
    print("\nÉ essa gravação que cria a árvore. ANTES, confira com device_list_dir se")
    print(f"  {base}{sep}{cliente}")
    print("já existe — se existir, é só somar esta subpasta datada, sem tocar no resto.")
    if nome_analise:
        print(f"\nSe '{nome_analise}' já existir, some um sufixo — '(2)' — em vez de")
        print("sobrescrever: análise do mesmo dia é revisão, não substituição.")


if __name__ == "__main__":
    main()
