import type { Metadata } from "next";

export const metadata: Metadata = { title: "Metodologia" };

export default function Metodologia() {
  return (
    <article className="prose prose-neutral mx-auto max-w-3xl dark:prose-invert">
      <h1>Metodologia e limitações</h1>
      <p>
        O Sonar Público cruza bases de dados oficiais e públicas para mostrar,
        em um só lugar, sanções, contratos e vínculos societários de empresas
        que negociam com o poder público. <strong>Apontamos vínculos — não
        acusamos.</strong>
      </p>

      <h2>De onde vêm os dados</h2>
      <ul>
        <li>
          <strong>Sanções:</strong> CEIS, CNEP, CEPIM e Acordos de Leniência,
          publicados pela CGU no Portal da Transparência (snapshot diário).
        </li>
        <li>
          <strong>Contratos:</strong> compras do Poder Executivo Federal
          (Portal da Transparência, mensal, desde 2024) e PNCP.
        </li>
        <li>
          <strong>Empresas e sócios:</strong> dados abertos do CNPJ da Receita
          Federal (mensal). O CPF dos sócios já vem parcialmente mascarado na
          origem (ex.: ***123456**) — nunca temos acesso ao documento completo.
        </li>
      </ul>

      <h2>Como detectamos vínculos</h2>
      <p>
        Duas empresas ficam vinculadas quando compartilham um sócio, comparado
        por <em>nome normalizado + fragmento visível do CPF</em>. Cada vínculo
        recebe um nível de confiança: <strong>alta</strong> (nome e fragmento
        de CPF idênticos) ou <strong>média</strong> (nome idêntico, documento
        ausente em uma das bases). Vínculos de média confiança nunca são
        apresentados como certeza.
      </p>
      <p>
        O aviso de <strong>possível sucessora</strong> aparece quando uma
        empresa vinculada foi aberta <em>depois</em> do início da sanção da
        relacionada, no mesmo ramo (CNAE) e município. É um sinal para
        verificação humana, não uma conclusão.
      </p>

      <h2>Limitações que você precisa conhecer</h2>
      <ul>
        <li>
          <strong>Homônimos:</strong> pessoas diferentes com o mesmo nome e o
          mesmo fragmento de CPF são raras, mas possíveis.
        </li>
        <li>
          <strong>Alcance jurídico das sanções varia:</strong> uma suspensão
          aplicada por um estado, em regra, impede contratos apenas com aquele
          ente. Um contrato federal com empresa suspensa por um estado pode ser
          perfeitamente legal. A declaração de inidoneidade, por outro lado,
          vale nacionalmente.
        </li>
        <li>
          <strong>Cobertura de contratos:</strong> Poder Executivo Federal
          desde 2024. Contratos estaduais e municipais estão no roadmap (a
          fonte, o PNCP, já está integrada).
        </li>
        <li>
          <strong>Defasagem:</strong> os dados do CNPJ são mensais; os demais,
          diários ou mensais. Diferenças de até 1 mês em relação à realidade
          são esperadas.
        </li>
        <li>
          <strong>Qualidade da origem:</strong> valores e datas são digitados
          por órgãos públicos e podem conter erros de registro.
        </li>
      </ul>

      <h2>Encontrou um erro?</h2>
      <p>
        O código é aberto e os dados são reprocessados a cada atualização.
        Reporte inconsistências pelo repositório do projeto.
      </p>
    </article>
  );
}
