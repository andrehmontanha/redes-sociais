# Caçada de tendências — YouTube, X, Instagram e TikTok

Buscar tendência só no Instagram é olhar o retrovisor. O formato que está no
Explorar hoje costuma ter nascido no TikTok semanas antes, e o assunto que vai
render post na semana que vem normalmente já está circulando no X. **A caçada
cobre as quatro plataformas com o mesmo conjunto de termos**, e o achado mora no
cruzamento.

O melhor resultado que este método produz tem sempre a mesma forma: *"este
formato já fez X milhões no TikTok, o nicho do cliente ainda não usou, e a
janela é de N semanas"*.

---

## Antes de sair caçando: monte a lista de termos

Sem termos, a caçada vira passeio. Monte de 8 a 12 termos em quatro camadas, a
partir do nicho detectado no Passo 3:

1. **Categoria** — o que o negócio é ("parque aquático", "operadora de turismo").
2. **Produto/serviço** — o que ele vende ("pacote Olímpia", "excursão").
3. **Momento do cliente** — como a pessoa fala quando quer ("viagem em família",
   "o que fazer em Olímpia", "resort com criança").
4. **Sazonal e regional** — o que está no calendário agora ("férias de julho",
   "feriado de 7 de setembro", "Olímpia SP").

A camada 3 é a que quase todo mundo esquece e é a que traz conteúdo de criador,
não de marca — que é onde as tendências realmente estão.

---

## YouTube

O melhor sinal de **durabilidade**: o que rende no YouTube tende a ter janela
maior que trend de TikTok, e o Shorts mostra o formato curto do mesmo nicho.

- Busca ordenada por mais recente: `https://www.youtube.com/results?search_query=<termo>&sp=CAI%253D`
- Shorts do nicho: `https://www.youtube.com/results?search_query=<termo>+%23shorts`
- Canal de um concorrente: aba *Vídeos* ordenada por **mais populares** — é o
  raio-x do que funciona para ele em formato longo.

Registre: título, canal, views, data, duração e o gancho dos 5 primeiros
segundos. Views no YouTube são públicas e comparáveis — é o número mais honesto
de toda a caçada.

---

## TikTok

É onde o formato nasce. Duas telas importam:

- Busca por termo, aba **Top**: `https://www.tiktok.com/search?q=<termo>`
- Busca por hashtag: `https://www.tiktok.com/tag/<termo>`
- **Áudio**: cada vídeo mostra a faixa no rodapé; clicar leva à página do som,
  que traz **quantos vídeos usam aquele áudio**. Esse contador é o melhor
  indicador de ciclo de vida que existe de graça — anote-o **com a data**, porque
  a variação entre duas análises é o que diz se a trend sobe ou satura.

Registre por vídeo: autor, views, curtidas, data, o áudio e o contador do áudio.

**Sem sessão logada o TikTok não devolve nada.** Não é rolagem limitada: numa
validação real a página de busca voltou com 172 caracteres e a de hashtag com
127 — só o menu e o botão "Entrar". Se o usuário não estiver logado no TikTok
nesse navegador, **peça que ele entre** e diga que a perna do TikTok fica de fora
até lá. Não finja que coletou.

---

## Instagram

Já coberto em `references/tendencias.md` — Explorar, Reels, áudios em alta e a
mineração dos seguidos. Aqui ele entra como **plataforma de chegada**: o teste é
se o formato que apareceu no TikTok e no YouTube já existe no Instagram do
nicho. Se não existe, é oportunidade; se já está em toda parte, é tarde.

**A página de busca do Explorar não renderiza nesta sessão** — o DOM volta com
o rodapé e nada mais. Mas o endpoint que ela chama funciona, de dentro da página
autenticada, e devolve o grid de resultados com curtidas e views:

```js
const H = {'X-IG-App-ID': '936619743392459'};
const j = await fetch('/api/v1/fbsearch/web/top_serp/?query=' +
                      encodeURIComponent(termo), {headers: H}).then(r => r.json());
for (const s of j.media_grid?.sections || []) {
  for (const m of (s.layout_content?.medias || [])) {
    const i = m.media; // i.user.username, i.like_count, i.play_count, i.taken_at
  }
}
```

Numa validação real isso devolveu 15 itens para "agente de ia", o maior deles
com 2,9 milhões de visualizações — informação que a leitura do DOM não dava.

---

## X

Não é fonte de formato — é fonte de **assunto e timing**. Serve para descobrir o
que a audiência do nicho comenta *esta semana*, e para pegar sazonalidade antes
dos outros.

**A extensão do Chrome precisa ter o x.com liberado.** Sem isso a navegação
volta "Navigation to this domain is not allowed" e a perna do X não roda — peça
ao usuário para liberar o domínio nas permissões de site da extensão.

- Busca recente: `https://x.com/search?q=<termo>&f=live`
- Busca por engajamento: `https://x.com/search?q=<termo>&f=top`
- Filtro útil: `<termo> min_faves:50` corta ruído.

Registre: o assunto, o volume aparente e um exemplo de post. **Não trate
tendência de X como formato de Reel** — traduza o assunto para o formato que já
funciona no perfil do cliente.

---

## Onde gravar

`dados/tendencias-<handle>.json`, com o campo `plataforma` em cada item — a trava
do dossiê confere se as quatro aparecem:

```json
{"coletado_em": "2026-08-27", "termos": ["..."],
 "itens": [
   {"plataforma": "tiktok", "url": "...", "autor": "...", "views": 0,
    "data": "2026-08-20", "formato": "...", "audio": "...",
    "videos_usando_o_audio": 0, "termo": "...", "observacao": "..."}
 ]}
```

---

## O cruzamento — a parte que vira dinheiro

| Tendência | YouTube | TikTok | Instagram | X | Leitura |
|---|---|---|---|---|---|
| formato X | alto | explodindo | ausente no nicho | — | **janela aberta** |
| assunto Y | — | — | saturado | alto | tarde para o formato, bom para pauta |

Três estados que decidem a recomendação:

- **Nasceu fora e ainda não chegou** → prioridade máxima. É a única situação em
  que o cliente entra cedo.
- **Está em todas** → só vale com ângulo próprio; sem diferencial é ruído.
- **Só no X** → é pauta, não formato. Vira legenda, carrossel ou roteiro.

Depois, estime a janela:

```bash
python scripts/ciclo_tendencia.py tendencias_<handle>.json
```

---

## O que baixar, e é obrigatório

Da caçada saem **no mínimo 3 vídeos de tendência e 5 áudios em alta**. A trava
do dossiê bloqueia sem eles.

Escolha por contraste, não por gosto: o de maior alcance, o de maior
engajamento por alcance e um do formato que o cliente ainda não usa. Depois:

```bash
python scripts/extrair_audio.py acervo/tendencias/videos/ --saida acervo/tendencias/audios/
```

O script separa a faixa, mede loudness e faixa dinâmica, calcula a energia por
segundo e marca os picos — o que permite cruzar **ritmo de áudio com ritmo de
corte** no teardown. Corte que cai no pico segura atenção; corte fora dele
parece aleatório.

**Áudio nunca é transcrito nem identificado automaticamente aqui.** Se a letra,
a fala ou o nome da faixa importarem, diga que não foram analisados — não
invente.

---

## Ritmo e limites

- Pausa de 2 a 4 segundos entre navegações, nas quatro plataformas.
- Nada de curtir, seguir, comentar ou postar.
- Se aparecer bloqueio, captcha ou "tente novamente mais tarde", **pare naquela
  plataforma**, registre até onde foi e siga nas outras. Nunca contorne.
- Conteúdo de terceiro coletado aqui é estudo. O que sai do dossiê é o teardown.
