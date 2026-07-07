"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export function BotaoVoltar() {
  const router = useRouter();
  return (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-2 text-muted-foreground"
      onClick={() => {
        // com histórico volta à busca de origem; por link direto, vai à home
        if (window.history.length > 1) router.back();
        else router.push("/");
      }}
    >
      <span aria-hidden>←</span> Voltar
    </Button>
  );
}
