import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function BarraBusca({
  defaultValue = "",
  tamanho = "md",
}: {
  defaultValue?: string;
  tamanho?: "md" | "lg";
}) {
  const altura = tamanho === "lg" ? "h-12 text-base" : "h-10";
  return (
    <form action="/busca" role="search" className="flex w-full max-w-xl gap-2">
      <label htmlFor="q" className="sr-only">
        Nome da empresa ou CNPJ
      </label>
      <Input
        id="q"
        name="q"
        type="search"
        required
        minLength={3}
        defaultValue={defaultValue}
        placeholder="Nome da empresa ou CNPJ"
        className={altura}
      />
      <Button type="submit" className={tamanho === "lg" ? "h-12" : "h-10"}>
        Buscar
      </Button>
    </form>
  );
}
