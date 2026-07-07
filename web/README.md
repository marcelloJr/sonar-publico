# web

Frontend do Sonar Público — Next.js 16 (App Router) + Tailwind 4 + shadcn/ui
(base Radix, por acessibilidade — WCAG 2.1 AA é entregável, ver SPEC P3.7).

## Rodar local

Precisa da API no ar (`make api` na raiz do monorepo, porta 8000) e do banco
gerado (`make pipeline-amostra`).

```sh
npm install
npm run dev     # http://localhost:3000
```

A URL da API vem de `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Estrutura

- `app/` — páginas: home (busca + números), `busca/`, `empresa/[cnpj]/`,
  `metodologia/`
- `lib/api.ts` — cliente tipado da API; `lib/glossario.ts` — explicações de
  sanções em linguagem simples; `lib/formato.ts` — CNPJ/moeda/data pt-BR
- `components/ui/` — shadcn/ui (copy-in); `components/` — componentes do projeto

Nota (Next 16): `params`/`searchParams` são Promises (`await` obrigatório) e
`fetch` em Server Component não é cacheado por padrão.
