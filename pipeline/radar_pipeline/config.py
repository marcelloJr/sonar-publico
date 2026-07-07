"""Configuração do pipeline (SPEC §3 — replicabilidade).

Três eixos: escopo (esfera/UF/município), período e modo. Qualquer pessoa
ajusta o ``config.toml`` da raiz e roda o pipeline no próprio recorte.
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ESFERAS_VALIDAS = {"F", "E", "M"}


@dataclass(frozen=True)
class Config:
    # escopo
    esferas: tuple[str, ...] = ("F",)
    uf: str | None = None
    codigo_municipio_ibge: str | None = None
    # período (compras/PNCP; sanções e CNPJ são snapshots)
    contratos_desde: str = "2024-01"
    # modo: amostra processa só 1 das 10 partes do QSA (viável em laptop)
    amostra: bool = False
    # caminhos
    dados: Path = field(default=Path("data"))

    def __post_init__(self) -> None:
        invalidas = set(self.esferas) - ESFERAS_VALIDAS
        if invalidas:
            raise ValueError(f"esferas inválidas: {sorted(invalidas)} (use F, E e/ou M)")
        partes = self.contratos_desde.split("-")
        valido = (
            len(partes) == 2
            and len(partes[0]) == 4
            and all(p.isdigit() for p in partes)
            and 1 <= int(partes[1]) <= 12
        )
        if not valido:
            raise ValueError(f"contratos_desde inválido: {self.contratos_desde!r} (use AAAA-MM)")

    @property
    def banco(self) -> Path:
        return self.dados / "sonar.duckdb"

    @property
    def raw(self) -> Path:
        return self.dados / "raw"

    @property
    def staging(self) -> Path:
        return self.dados / "staging"

    @classmethod
    def carrega(cls, caminho: Path | None = None) -> "Config":
        """Lê o config.toml (defaults se ausente); caminhos relativos à raiz do repo."""
        raiz = Path(__file__).resolve().parents[2]
        caminho = caminho or raiz / "config.toml"
        bruto: dict = {}
        if caminho.exists():
            with caminho.open("rb") as f:
                bruto = tomllib.load(f)
        escopo = bruto.get("escopo", {})
        dados = Path(bruto.get("caminhos", {}).get("dados", "data"))
        if not dados.is_absolute():
            dados = raiz / dados
        return cls(
            esferas=tuple(escopo.get("esferas", ["F"])),
            uf=escopo.get("uf") or None,
            codigo_municipio_ibge=str(escopo["codigo_municipio_ibge"])
            if escopo.get("codigo_municipio_ibge")
            else None,
            contratos_desde=bruto.get("periodo", {}).get("contratos_desde", "2024-01"),
            amostra=bool(bruto.get("modo", {}).get("amostra", False)),
            dados=dados,
        )
