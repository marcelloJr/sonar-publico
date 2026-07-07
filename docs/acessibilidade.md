# Acessibilidade (P3.7)

> Auditoria Lighthouse (categoria *accessibility*), executada em 07/07/2026
> contra o build de desenvolvimento com dados completos. Meta do SPEC: ≥ 90.

| Página | Score |
|---|---|
| Home (`/`) | **100** |
| Busca (`/busca`) | **100** |
| Ficha da empresa (`/empresa/[cnpj]`) | **100** |
| Órgãos (`/orgaos`) | **100** |
| Órgão (`/orgao/[codigo]`) | **100** |
| Metodologia (`/metodologia`) | **100** |

## Práticas aplicadas

- **Semântica**: landmarks (`header/nav/main/footer`), headings hierárquicos,
  `dl/dt/dd` para pares rótulo-valor, `lang="pt-BR"`.
- **Teclado**: skip link ("pular para o conteúdo"), foco visível, nós do grafo
  focáveis e acionáveis por Enter/Espaço, zoom do grafo por botões.
- **Cor nunca é o único canal**: badges de risco têm texto ("Sanção vigente"),
  linha do grafo diferencia confiança por tracejado, legenda textual.
- **Contraste AA**: paleta conferida; o badge âmbar de grau 1 usa `amber-700`
  (o tom 600 reprovava com texto branco em fonte pequena — achado da auditoria).
- **Leitores de tela**: `aria-label` em controles e no SVG do grafo,
  `aria-live` no feedback de "copiado", `role="search"` no formulário.
- **shadcn/ui sobre Radix**: comportamento acessível de accordion e afins.

## Como re-auditar

```sh
npx lighthouse http://localhost:3000 --only-categories=accessibility
```

Repetir após mudanças visuais relevantes. Score < 100 não bloqueia merge, mas
< 90 sim (meta do SPEC §9.5).
