import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function EmpresaNaoEncontrada() {
  return (
    <div className="mx-auto max-w-xl space-y-4 py-16 text-center">
      <h1 className="text-2xl font-bold">Empresa fora do radar</h1>
      <p className="text-muted-foreground">
        Não encontramos esta empresa no universo do Sonar Público. Isso
        geralmente é um bom sinal: cobrimos empresas com sanção registrada,
        contrato público federal recente ou vínculo societário com alguma
        sancionada.
      </p>
      <Button asChild>
        <Link href="/">Fazer outra busca</Link>
      </Button>
    </div>
  );
}
