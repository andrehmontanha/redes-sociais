import { test } from "node:test";
import assert from "node:assert/strict";
import { aplicar, validarEnvio, vencido, type Envio, type Item } from "../lib/fila.ts";
import { impressao, sha256, strPy } from "../lib/impressao.ts";

// Vetores gerados com o `fila.impressao()` do estúdio (Python) sobre os mesmos
// bytes — se divergirem, a aprovação dada no estúdio deixa de valer no webapp.
test("impressão digital igual à do fila.py", () => {
  const a = sha256("peca-um");
  const b = sha256("peca-dois");
  assert.equal(
    impressao([a, b], {
      tipo: "carrossel",
      legenda: "Olá, mundo!\n\n#ia d'água",
      agendado_para: "2026-10-03T18:30:00-03:00",
      thumb_offset_ms: null,
      avatares: [],
    }),
    "d7a3370a2d4aab0b8dee5594aff517e88baa3be41c3b0a0dbce3deea3c12c8c5",
  );
  assert.equal(
    impressao([a, b], { tipo: "reel", legenda: "x", agendado_para: null, thumb_offset_ms: 1500, avatares: ["Ana Lu", "O'Neil"] }),
    "e10c119fa30480443445175d1dd04d3af50feb7c404c3a750836a21525e5e68a",
  );
});

test("str() do Python", () => {
  assert.equal(strPy(null), "None");
  assert.equal(strPy([]), "[]");
  assert.equal(strPy(["a", "O'Neil"]), `['a', "O'Neil"]`);
  assert.equal(strPy(1000), "1000");
});

const envio = (extra: Partial<Envio> = {}): Envio => ({
  nome: "20261001-011152-feed",
  cliente: "braturix",
  tipo: "feed",
  legenda: "legenda",
  agendado_para: "2026-10-03T12:00:00-03:00",
  thumb_offset_ms: null,
  avatares: [],
  midias: [{ url: "https://x.public.blob.vercel-storage.com/fila/braturix/i/01-abc.jpg", pathname: "fila/braturix/i/01-abc.jpg", nome: "01.jpg" }],
  ...extra,
});

test("envio válido passa; regras do fila.py valem aqui", () => {
  assert.deepEqual(validarEnvio(envio()), []);
  assert.ok(validarEnvio(envio({ agendado_para: "2026-10-03T12:00:00" })).some((e) => e.includes("fuso")));
  assert.ok(validarEnvio(envio({ tipo: "carrossel" })).some((e) => e.includes("de 2 a 10")));
  assert.ok(validarEnvio(envio({ avatares: ["Ana"] })).some((e) => e.includes("avatar")));
  assert.ok(validarEnvio(envio({ legenda: "#a ".repeat(31) })).some((e) => e.includes("hashtags")));
  const fora = envio({ midias: [{ url: "https://x/y.jpg", pathname: "fila/outro/i/01.jpg", nome: "01.jpg" }] });
  assert.ok(validarEnvio(fora).some((e) => e.includes("fora da pasta")));
});

const item = (extra: Partial<Item> = {}): Item => ({
  id: "braturix--x",
  cliente: "braturix",
  tipo: "feed",
  legenda: "l",
  agendado_para: "2026-10-03T12:00:00-03:00",
  thumb_offset_ms: null,
  avatares: [],
  status: "aguardando_aprovacao",
  criadoEm: "2026-10-01T00:00:00Z",
  midias: [],
  capa: null,
  impressao: "abc",
  aprovacao: null,
  historico: [],
  ...extra,
});

test("aprovar grava nome e impressão; exige nome", () => {
  const ok = aplicar(item(), { tipo: "aprovar", por: "André" }, "2026-10-01T10:00:00Z");
  assert.ok(typeof ok !== "string");
  assert.equal(ok.status, "aprovado");
  assert.deepEqual(ok.aprovacao, { por: "André", em: "2026-10-01T10:00:00Z", impressao: "abc", origem: "painel", mensagem: null });
  assert.equal(typeof aplicar(item(), { tipo: "aprovar", por: " " }), "string");
});

test("não se aprova o que já foi publicado nem o rejeitado", () => {
  assert.equal(typeof aplicar(item({ status: "publicado" }), { tipo: "aprovar", por: "André" }), "string");
  assert.equal(typeof aplicar(item({ status: "rejeitado" }), { tipo: "aprovar", por: "André" }), "string");
});

test("rejeitar exige motivo e limpa a aprovação", () => {
  const aprovado = item({ status: "aprovado", aprovacao: { por: "A", em: "", impressao: "abc", origem: "painel" } });
  assert.equal(typeof aplicar(aprovado, { tipo: "rejeitar", por: "André", motivo: "" }), "string");
  const r = aplicar(aprovado, { tipo: "rejeitar", por: "André", motivo: "trocar a capa" });
  assert.ok(typeof r !== "string");
  assert.equal(r.status, "rejeitado");
  assert.equal(r.aprovacao, null);
});

test("tentar de novo só com a aprovação ainda válida", () => {
  const comErro = item({ status: "erro", erro: "x", aprovacao: { por: "A", em: "", impressao: "abc", origem: "painel" } });
  const r = aplicar(comErro, { tipo: "tentar_de_novo", por: "André" });
  assert.ok(typeof r !== "string" && r.status === "aprovado");
  const mudou = item({ status: "erro", aprovacao: { por: "A", em: "", impressao: "outra", origem: "painel" } });
  assert.equal(typeof aplicar(mudou, { tipo: "tentar_de_novo", por: "André" }), "string");
});

test("vencido só para aprovado no horário", () => {
  const aprovado = item({ status: "aprovado", aprovacao: { por: "A", em: "", impressao: "abc", origem: "painel" } });
  const meioDia = Date.parse("2026-10-03T15:00:00Z");
  assert.equal(vencido(aprovado, meioDia - 1), false);
  assert.equal(vencido(aprovado, meioDia), true);
  assert.equal(vencido(item(), meioDia + 1), false, "sem aprovação não publica");
  assert.equal(vencido({ ...aprovado, aprovacao: null }, meioDia + 1), false);
});
