"use client";

import { useState } from "react";

export default function Copiar({ texto }: { texto: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      className="botao primario"
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(texto);
        setOk(true);
      }}
    >
      {ok ? "Copiado ✓" : "Copiar URL"}
    </button>
  );
}
