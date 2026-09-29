import { test } from "node:test";
import assert from "node:assert/strict";
import { abrir, iguais, selar } from "../lib/cripto.ts";
import { brutoDemo } from "../lib/demo.ts";
import { capa, formato, mediana, montarPosts, resumir } from "../lib/resumo.ts";

const SEGREDO = "x".repeat(40);

test("selar e abrir devolvem o mesmo dado", () => {
  const dado = [{ usuario: "cliente", token: "IGAAsegredo" }];
  const selado = selar(dado, SEGREDO, "contas");
  assert.ok(!selado.includes("IGAAsegredo"), "token não pode aparecer em claro no cookie");
  assert.deepEqual(abrir(selado, SEGREDO, "contas"), dado);
});

test("cookie adulterado ou com outro segredo vira nulo", () => {
  const selado = selar({ a: 1 }, SEGREDO, "contas");
  const adulterado = selado.slice(0, -2) + (selado.endsWith("A") ? "BB" : "AA");
  assert.equal(abrir(adulterado, SEGREDO, "contas"), null);
  assert.equal(abrir(selado, "y".repeat(40), "contas"), null);
  assert.equal(abrir(selado, SEGREDO, "sessao"), null, "finalidade diferente não abre");
});

test("comparação de senha", () => {
  assert.ok(iguais("abc12345", "abc12345"));
  assert.ok(!iguais("abc12345", "abc12346"));
});

test("mediana ignora nulos", () => {
  assert.equal(mediana([3, null, 1, 2]), 2);
  assert.equal(mediana([1, 2, 3, 4]), 2.5);
  assert.equal(mediana([null]), null);
});

test("formato por tipo de mídia", () => {
  assert.equal(formato({ id: "1", media_type: "VIDEO", media_product_type: "REELS", timestamp: "" }), "reel");
  assert.equal(formato({ id: "1", media_type: "CAROUSEL_ALBUM", media_product_type: "FEED", timestamp: "" }), "carrossel");
  assert.equal(formato({ id: "1", media_type: "IMAGE", media_product_type: "FEED", timestamp: "" }), "imagem");
});

test("horário convertido para Brasília", () => {
  const [p] = montarPosts({
    perfil: { username: "x" }, conta_insights: {}, insights: {},
    midias: [{ id: "1", media_type: "IMAGE", timestamp: "2026-09-28T21:00:00+0000" }],
  });
  assert.equal(p.data, "2026-09-28");
  assert.equal(p.hora, "18:00");
  assert.equal(p.janela, 3);
  assert.equal(p.dia, 1); // segunda
});

test("resumo da demonstração", () => {
  const r = resumir(brutoDemo());
  assert.equal(r.posts.length, 30);
  assert.equal(r.semInsights, 1);
  assert.ok(r.kpis.alcanceMediano! > 0);
  assert.equal(r.topAlcance.length, 5);
  assert.ok(r.topAlcance[0].alcance! >= r.topAlcance[4].alcance!);
  assert.ok(r.porFormato.length >= 2);
  for (const linha of r.grade) for (const c of linha) if (c.alcance != null) assert.ok(c.posts >= 3);
});

test("taxa de salvamento é salvamento sobre alcance", () => {
  const [p] = montarPosts({
    perfil: { username: "x" }, conta_insights: {},
    midias: [{ id: "1", media_type: "IMAGE", timestamp: "2026-09-28T12:00:00+0000" }],
    insights: { "1": { reach: 2000, saved: 50, shares: 10 } },
  });
  assert.equal(p.taxaSalvamento, 2.5);
  assert.equal(p.taxaCompartilhamento, 0.5);
});

test("capa nunca é um MP4", () => {
  const base = { id: "1", timestamp: "2026-09-28T12:00:00+0000" };
  assert.equal(capa({ ...base, media_type: "VIDEO", media_url: "https://x/v.mp4?a=1", thumbnail_url: "https://x/t.jpg" }), "https://x/t.jpg");
  assert.equal(capa({ ...base, media_type: "IMAGE", media_url: "https://x/i.jpg" }), "https://x/i.jpg");
  assert.equal(capa({ ...base, media_type: "CAROUSEL_ALBUM", media_url: "https://x/v.mp4",
    children: { data: [{ id: "a", media_type: "VIDEO", media_url: "https://x/v.mp4", thumbnail_url: "https://x/c.jpg" }] } }), "https://x/c.jpg");
  assert.equal(capa({ ...base, media_type: "CAROUSEL_ALBUM", media_url: "https://x/v.mp4" }), undefined);
});

test("rankings de salvamento ignoram zeros", () => {
  const r = resumir({
    perfil: { username: "x", followers_count: 50 }, conta_insights: {},
    midias: ["1", "2", "3"].map((id) => ({ id, media_type: "IMAGE" as const, timestamp: "2026-09-28T12:00:00+0000" })),
    insights: { "1": { reach: 100, saved: 0, shares: 0 }, "2": { reach: 50, saved: 2, shares: 0 }, "3": { reach: 20, saved: 0, shares: 1 } },
  });
  assert.deepEqual(r.topSalvamento.map((p) => p.id), ["2"]);
  assert.deepEqual(r.topCompartilhamento.map((p) => p.id), ["3"]);
  assert.equal(r.topAlcance.length, 3);
});
