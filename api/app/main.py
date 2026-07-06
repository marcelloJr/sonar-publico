from fastapi import FastAPI

app = FastAPI(
    title="Sonar Público — API",
    description=(
        "API pública que cruza sanções (CEIS/CNEP/CEPIM/Leniência), contratos "
        "federais e quadro societário. Dados: Portal da Transparência e Receita "
        "Federal, catalogados no dados.gov.br."
    ),
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
