# Raspagem de sites — Firecrawl e as alternativas

O feed diz o que a marca **posta**, a biblioteca de anúncios diz o que ela
**compra**, e o site diz o que ela **vende**. Sem o terceiro, o dossiê recomenda
conteúdo sem saber qual é a oferta — e é assim que se produz plano de mídia que
não converte.

## Antes de tudo: confira o que o Firecrawl conectado sabe fazer

**Firecrawl não é uma coisa só.** O conector distribuído em claude.ai que
encontramos numa validação real expõe **apenas busca**:

| Ferramenta | O que devolve |
|---|---|
| `firecrawl_search` | título, URL e descrição dos resultados — **não o conteúdo da página** |
| `firecrawl_developer_search` | o mesmo, no índice de repositórios e documentação |
| `firecrawl_research_*` | literatura acadêmica |

Não havia `firecrawl_scrape`, `firecrawl_crawl` nem `firecrawl_extract`. **Olhe
a sua lista de ferramentas antes de planejar a raspagem em cima do Firecrawl** —
se só existir `firecrawl_search`, o conteúdo das páginas vem do `WebFetch`, e o
Firecrawl entra para outras duas coisas, descritas abaixo, que ele faz melhor
que qualquer alternativa.

### Uso 1 — mapear o site com `site:`

`firecrawl_search` com a query `site:<dominio>` responde uma pergunta que o
`WebFetch` não responde: **quantas páginas esse site tem no índice, e quais**.

Numa validação real, `site:afinix.com.br` voltou com **1 página indexada** — sem
blog, sem página por operadora, sem página por cidade. Isso é diagnóstico, não
trivia: um concorrente com trinta páginas indexadas está capturando busca
orgânica que o cliente não captura, e a comparação dos números de páginas entre
cliente e concorrentes é uma linha do dossiê que sai de graça.

### Uso 2 — descobrir concorrentes reais do nicho e da região

Busque o termo do nicho com a cidade (`plano de saúde empresarial São José do
Rio Preto`) e, para achar perfis, use `includeDomains: ["instagram.com"]`. A
descrição dos resultados costuma trazer **o handle e a contagem de seguidores**,
o que dá uma lista de candidatos a perfil de comparação sem abrir o navegador.

Confira cada candidato no Instagram antes de adotá-lo: a descrição do resultado
de busca pode estar desatualizada, e número que entra no relatório vem da
coleta, nunca do snippet.

---

## A ordem de preferência para o **conteúdo** da página

**1. `firecrawl_scrape`, se existir na sua lista.** Rota limpa: markdown
estruturado, respeita robots, lida com JavaScript. Não conte com ela sem ter
visto o nome na lista de ferramentas.

**2. `WebFetch`.** Resolve a maioria dos sites institucionais e foi o que
sustentou a validação real. Uma URL por chamada, com um prompt do que extrair.
É a rota padrão.

**3. O navegador do usuário.** Para o que exige sessão logada, ou quando a
página só monta com JavaScript pesado. `get_page_text` para o texto,
`javascript_tool` para ler estrutura, `computer screenshot` para o visual.

Registre em `dados/sites-<handle>.json` **qual rota foi usada**, no campo
`metodo`. Daqui a seis meses a diferença entre "o site não dizia" e "a
ferramenta não leu" é a diferença entre um achado e um erro.

**Se as três falharem, o site não foi raspado.** Escreva isso no dossiê. Não
tente proxies, espelhos, cache de terceiros ou qualquer rota alternativa —
inclusive quando `WebFetch` disser que o domínio está bloqueado. Domínio
bloqueado é resposta final.

---

## O que extrair de cada site

Não colecione páginas — colecione respostas. Seis campos, os mesmos para o
cliente e para cada concorrente, senão a comparação não fecha:

| Campo | Por que importa |
|---|---|
| **Oferta** | O que exatamente se compra ali, em uma frase |
| **Preço** | Quando público. "Sob consulta" também é um dado — muda o funil |
| **Prova** | Depoimento, selo, número de clientes, tempo de mercado |
| **CTA** | WhatsApp, formulário, checkout ou telefone. Define o funil inteiro |
| **Captura** | Tem newsletter, cupom, cotação? É onde o social vira lista |
| **Promessa do topo** | O primeiro H1: é o posicionamento declarado |
| **Páginas indexadas** | De `site:<dominio>`. Um site de 1 página não disputa busca |

Grave em `dados/sites-<handle>.json`, uma entrada por domínio, com a data.

## O sétimo campo, que é de graça: as contradições

Leia o site e a bio lado a lado. Numa validação real o site dizia **"há 5
anos"** e a bio do Instagram dizia **"Há 9 anos"** — a mesma prova social com
números diferentes, escrita pela mesma empresa. Tempo de mercado, número de
clientes e o nome do serviço são os três que mais divergem. Anote toda
divergência: é conserto de meia hora e é a única recomendação do dossiê que não
depende de nenhum número de desempenho.

## O cruzamento que vale

A pergunta é sempre a mesma: **o que o site vende aparece no feed?**

O padrão mais comum e mais caro é o inverso — o site vende pacote com preço
parcelado e o feed posta paisagem. Quando isso aparece, é o achado central do
dossiê, porque explica alcance alto com venda baixa sem precisar de mais nenhum
número.

Compare também a **promessa do topo** do cliente com a dos concorrentes. Se
todas dizem a mesma coisa, o espaço vago é de posicionamento, não de conteúdo.

---

## Limites

- Só conteúdo público. Nada de área logada, nada de contornar paywall ou
  bloqueio.
- Ritmo humano entre requisições; sem varredura de site inteiro quando cinco
  páginas respondem a pergunta.
- Texto de concorrente é **evidência citada**, não material a reaproveitar:
  cite trecho curto entre aspas, com a fonte, e não copie a página para o
  cliente.
- Dado pessoal que apareça no caminho (nome em depoimento, telefone de contato)
  entra de forma agregada ou não entra.
