"use client";

import { useRef, useState } from "react";

export function BotaoCopiar({ texto, rotulo }: { texto: string; rotulo: string }) {
  const [copiado, setCopiado] = useState(false);
  const temporizador = useRef<ReturnType<typeof setTimeout> | null>(null);

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(texto);
    } catch {
      // contexto sem Clipboard API (http fora do localhost): fallback clássico
      const area = document.createElement("textarea");
      area.value = texto;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    setCopiado(true);
    if (temporizador.current) clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => setCopiado(false), 1500);
  };

  return (
    <button
      type="button"
      onClick={copiar}
      aria-label={`Copiar ${rotulo}`}
      title={`Copiar ${rotulo}`}
      className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 align-middle text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2"
    >
      {copiado ? "✓ copiado" : "copiar"}
      <span aria-live="polite" className="sr-only">
        {copiado ? `${rotulo} copiado para a área de transferência` : ""}
      </span>
    </button>
  );
}
