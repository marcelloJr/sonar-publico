import { Badge } from "@/components/ui/badge";

// Cor NUNCA é o único canal (WCAG 1.4.1): o texto nomeia o grau.
export function BadgeGrau({
  grau,
  indicioSucessora = false,
}: {
  grau: number | null;
  indicioSucessora?: boolean;
}) {
  if (grau === 0) {
    return (
      <Badge className="bg-red-700 text-white hover:bg-red-700">
        Sanção vigente
      </Badge>
    );
  }
  if (grau === 1) {
    return (
      <Badge className="bg-amber-600 text-white hover:bg-amber-600">
        {indicioSucessora
          ? "Vínculo com sancionada · possível sucessora"
          : "Vínculo com sancionada"}
      </Badge>
    );
  }
  return <Badge variant="outline">Sem alerta nos dados</Badge>;
}
