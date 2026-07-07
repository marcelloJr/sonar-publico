"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import { Button } from "@/components/ui/button";
import { API_URL, type Grafo, type NoGrafo } from "@/lib/api";

type No = NoGrafo & SimulationNodeDatum;
// arestas AGREGADAS: uma por par de empresas, com todos os sócios em comum
// (o dado bruto traz uma aresta por sócio — 5 sócios = 5 linhas sobrepostas)
type Aresta = SimulationLinkDatum<No> & {
  socios: string[];
  confianca: string;
};
type Caixa = { x: number; y: number; w: number; h: number };

const COR_GRAU: Record<string, string> = {
  "0": "#b91c1c", // vermelho: sanção vigente
  "1": "#d97706", // âmbar: vínculo com sancionada
};

function corDoNo(grau: number | null): string {
  return COR_GRAU[String(grau)] ?? "#737373";
}

export function GrafoVinculos({ cnpj }: { cnpj: string }) {
  const [profundidade, setProfundidade] = useState(1);
  // estado derivado: "carregando" = a resposta guardada não é da profundidade
  // atual (evita setState síncrono no effect — react-hooks/set-state-in-effect)
  const [resposta, setResposta] = useState<{
    profundidade: number;
    grafo: Grafo | null;
  } | null>(null);

  useEffect(() => {
    let ativo = true;
    fetch(`${API_URL}/empresas/${cnpj}/grafo?profundidade=${profundidade}`, {
      cache: "no-store",
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((g: Grafo) => ativo && setResposta({ profundidade, grafo: g }))
      .catch(() => ativo && setResposta({ profundidade, grafo: null }));
    return () => {
      ativo = false;
    };
  }, [cnpj, profundidade]);

  const atual = resposta?.profundidade === profundidade ? resposta : null;
  const dados = atual?.grafo ?? null;
  const estado = atual === null ? "carregando" : dados === null ? "erro" : "ok";

  const layout = useMemo(() => {
    if (!dados || dados.arestas.length === 0) return null;
    // garante nó para todo id citado nas arestas (defesa extra à API)
    const porId = new Map<string, No>(dados.nos.map((n) => [n.id, { ...n }]));
    for (const a of dados.arestas) {
      for (const id of [a.cnpj_a, a.cnpj_b]) {
        if (!porId.has(id)) porId.set(id, { id, nome: null, grau: null });
      }
    }
    const nos = [...porId.values()];
    const porPar = new Map<string, Aresta>();
    for (const a of dados.arestas) {
      const chave = `${a.cnpj_a}|${a.cnpj_b}`;
      const existente = porPar.get(chave);
      if (existente) {
        if (!existente.socios.includes(a.socio_comum)) existente.socios.push(a.socio_comum);
        if (a.confianca === "alta") existente.confianca = "alta";
      } else {
        porPar.set(chave, {
          source: a.cnpj_a,
          target: a.cnpj_b,
          socios: [a.socio_comum],
          confianca: a.confianca,
        });
      }
    }
    const arestas = [...porPar.values()];
    // grafos densos precisam de mais repulsão e links mais longos p/ abrir
    const denso = nos.length > 18;
    forceSimulation(nos)
      .force(
        "link",
        forceLink<No, Aresta>(arestas).id((n) => n.id).distance(denso ? 180 : 130)
      )
      .force("charge", forceManyBody().strength(denso ? -900 : -400))
      .force("center", forceCenter(0, 0))
      .force("collide", forceCollide(denso ? 48 : 40))
      .stop()
      .tick(300);
    const xs = nos.map((n) => n.x ?? 0);
    const ys = nos.map((n) => n.y ?? 0);
    const margem = 70;
    const caixa: Caixa = {
      x: Math.min(...xs) - margem,
      y: Math.min(...ys) - margem,
      w: Math.max(...xs) - Math.min(...xs) + margem * 2,
      h: Math.max(...ys) - Math.min(...ys) + margem * 2,
    };
    return { nos, arestas, caixa };
  }, [dados]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2" role="group" aria-label="Profundidade do grafo">
          {[1, 2].map((p) => (
            <Button
              key={p}
              size="sm"
              variant={profundidade === p ? "default" : "outline"}
              aria-pressed={profundidade === p}
              onClick={() => setProfundidade(p)}
            >
              {p === 1 ? "Vizinhos diretos" : "2 graus"}
            </Button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          <span className="mr-3">
            <span aria-hidden className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-red-700" />
            sanção vigente
          </span>
          <span className="mr-3">
            <span aria-hidden className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-amber-600" />
            vínculo com sancionada
          </span>
          <span className="mr-3">linha grossa = mais sócios em comum</span>
          <span>tracejada = confiança média</span>
        </p>
      </div>

      {estado === "carregando" && (
        <p className="py-12 text-center text-muted-foreground">Montando o grafo…</p>
      )}
      {estado === "erro" && (
        <p role="alert" className="py-12 text-center text-muted-foreground">
          Não foi possível carregar o grafo agora.
        </p>
      )}
      {estado === "ok" && !layout && (
        <p className="py-12 text-center text-muted-foreground">
          Nenhum vínculo societário registrado para esta empresa.
        </p>
      )}

      {layout && dados && (
        <GrafoSvg
          key={`${cnpj}-${profundidade}`}
          layout={layout}
          centro={dados.centro}
          cnpj={cnpj}
        />
      )}
    </div>
  );
}

function GrafoSvg({
  layout,
  centro,
  cnpj,
}: {
  layout: { nos: No[]; arestas: Aresta[]; caixa: Caixa };
  centro: string;
  cnpj: string;
}) {
  const router = useRouter();
  const svgRef = useRef<SVGSVGElement>(null);
  // zoom/pan sobre a caixa base; remonta (e reseta) quando muda profundidade
  const [vista, setVista] = useState<Caixa>(layout.caixa);
  const arrasto = useRef<{ px: number; py: number; vx: number; vy: number } | null>(null);
  // nó sob o mouse/foco de teclado: destaca a vizinhança e esmaece o resto
  const [foco, setFoco] = useState<string | null>(null);

  // "denso" esconde rótulos genéricos — mas zoom revela: com a vista a menos
  // de 60% da caixa original há espaço de tela suficiente pra rotular tudo
  const ampliado = vista.w < layout.caixa.w * 0.6;
  const denso = layout.nos.length > 18 && !ampliado;
  const vizinhosDoFoco = useMemo(() => {
    if (!foco) return null;
    const conjunto = new Set<string>([foco]);
    for (const a of layout.arestas) {
      const s = (a.source as No).id;
      const t = (a.target as No).id;
      if (s === foco) conjunto.add(t);
      if (t === foco) conjunto.add(s);
    }
    return conjunto;
  }, [foco, layout.arestas]);

  const aplicaZoom = (fator: number) => {
    setVista((v) => {
      const w = v.w * fator;
      const h = v.h * fator;
      return { x: v.x + (v.w - w) / 2, y: v.y + (v.h - h) / 2, w, h };
    });
  };

  const baixar = (formato: "svg" | "png") => {
    const svg = svgRef.current;
    if (!svg) return;
    const clone = svg.cloneNode(true) as SVGSVGElement;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("font-family", "ui-sans-serif, system-ui, sans-serif");
    // exporta o grafo inteiro, independente do zoom atual
    const { x, y, w, h } = layout.caixa;
    clone.setAttribute("viewBox", `${x} ${y} ${w} ${h}`);
    clone.style.background = "#ffffff";
    const texto = new XMLSerializer().serializeToString(clone);
    const nome = `sonar-grafo-${cnpj}`;
    if (formato === "svg") {
      const blob = new Blob([texto], { type: "image/svg+xml" });
      dispara(URL.createObjectURL(blob), `${nome}.svg`);
      return;
    }
    const imagem = new Image();
    const url = URL.createObjectURL(new Blob([texto], { type: "image/svg+xml" }));
    imagem.onload = () => {
      const escala = 2;
      const canvas = document.createElement("canvas");
      canvas.width = w * escala;
      canvas.height = h * escala;
      const ctx = canvas.getContext("2d")!;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(imagem, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => blob && dispara(URL.createObjectURL(blob), `${nome}.png`));
    };
    imagem.src = url;
  };

  const dispara = (url: string, nome: string) => {
    const a = document.createElement("a");
    a.href = url;
    a.download = nome;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Zoom" className="flex gap-1">
          <Button size="sm" variant="outline" aria-label="Aproximar" onClick={() => aplicaZoom(1 / 1.4)}>
            +
          </Button>
          <Button size="sm" variant="outline" aria-label="Afastar" onClick={() => aplicaZoom(1.4)}>
            −
          </Button>
          <Button size="sm" variant="outline" onClick={() => setVista(layout.caixa)}>
            Ajustar
          </Button>
        </div>
        <span className="text-xs text-muted-foreground">arraste para mover</span>
        <div className="ml-auto flex gap-1">
          <Button size="sm" variant="outline" onClick={() => baixar("png")}>
            Baixar PNG
          </Button>
          <Button size="sm" variant="outline" onClick={() => baixar("svg")}>
            Baixar SVG
          </Button>
        </div>
      </div>

      <svg
        ref={svgRef}
        viewBox={`${vista.x} ${vista.y} ${vista.w} ${vista.h}`}
        role="img"
        aria-label={`Grafo de vínculos societários: ${layout.nos.length} empresas e ${layout.arestas.length} vínculos. Clique em uma empresa para abrir a ficha.`}
        className="h-105 w-full cursor-grab touch-none rounded-lg border bg-muted/20 active:cursor-grabbing"
        onPointerDown={(e) => {
          (e.target as Element).setPointerCapture?.(e.pointerId);
          arrasto.current = { px: e.clientX, py: e.clientY, vx: vista.x, vy: vista.y };
        }}
        onPointerMove={(e) => {
          const a = arrasto.current;
          const svg = svgRef.current;
          if (!a || !svg) return;
          const proporcao = vista.w / svg.clientWidth;
          setVista((v) => ({
            ...v,
            x: a.vx - (e.clientX - a.px) * proporcao,
            y: a.vy - (e.clientY - a.py) * proporcao,
          }));
        }}
        onPointerUp={() => (arrasto.current = null)}
        onPointerLeave={() => (arrasto.current = null)}
      >
        {layout.arestas.map((a, i) => {
          const s = a.source as No;
          const t = a.target as No;
          const noFoco = foco !== null && (s.id === foco || t.id === foco);
          const opacidade = foco ? (noFoco ? 0.85 : 0.04) : denso ? 0.22 : 0.5;
          // vector-effect non-scaling-stroke: espessura constante em pixels
          // de tela — o zoom não engorda as linhas
          return (
            <line
              key={i}
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke={noFoco ? "#525252" : "#b5b5b5"}
              strokeWidth={Math.min(1 + (a.socios.length - 1) * 0.75, 4)}
              strokeOpacity={opacidade}
              strokeDasharray={a.confianca === "media" ? "5 4" : undefined}
              vectorEffect="non-scaling-stroke"
            >
              <title>
                {a.socios.length === 1
                  ? `Sócio em comum: ${a.socios[0]}`
                  : `${a.socios.length} sócios em comum: ${a.socios.slice(0, 6).join("; ")}${a.socios.length > 6 ? "…" : ""}`}
                {` (confiança ${a.confianca})`}
              </title>
            </line>
          );
        })}
        {layout.nos.map((n) => {
          const ehCentro = n.id === centro;
          const destacado = vizinhosDoFoco?.has(n.id) ?? true;
          // em grafo denso, rótulo só p/ centro, sancionadas e vizinhança focada
          const mostraRotulo = foco
            ? destacado
            : !denso || ehCentro || n.grau === 0;
          return (
            <g
              key={n.id}
              role="link"
              tabIndex={0}
              aria-label={`${n.nome ?? `raiz ${n.id}`}${ehCentro ? " (empresa desta ficha)" : ""} — abrir ficha`}
              className="cursor-pointer focus:outline-2 focus:outline-offset-2"
              opacity={destacado ? 1 : 0.25}
              onMouseEnter={() => setFoco(n.id)}
              onMouseLeave={() => setFoco(null)}
              onFocus={() => setFoco(n.id)}
              onBlur={() => setFoco(null)}
              onClick={() => !ehCentro && router.push(`/empresa/${n.id}`)}
              onKeyDown={(e) => {
                if ((e.key === "Enter" || e.key === " ") && !ehCentro) {
                  e.preventDefault();
                  router.push(`/empresa/${n.id}`);
                }
              }}
            >
              <circle
                cx={n.x}
                cy={n.y}
                r={ehCentro ? 16 : 10}
                fill={corDoNo(n.grau)}
                stroke={ehCentro ? "#171717" : "#fff"}
                strokeWidth={ehCentro ? 3 : 1.5}
              >
                <title>{n.nome ?? `raiz ${n.id}`}</title>
              </circle>
              {mostraRotulo && (
                <text
                  x={n.x}
                  y={(n.y ?? 0) + (ehCentro ? 30 : 23)}
                  textAnchor="middle"
                  fontSize={9}
                  fontWeight={ehCentro || n.id === foco ? 700 : 400}
                  fill="#171717"
                  paintOrder="stroke"
                  stroke="#ffffff"
                  strokeWidth={3}
                >
                  {(n.nome ?? `raiz ${n.id}`).slice(0, 28)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
