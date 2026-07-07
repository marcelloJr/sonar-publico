.PHONY: setup lint format test api pipeline pipeline-amostra

setup:            ## Instala todas as dependências (uv workspace)
	uv sync --all-packages

lint:             ## Ruff em todo o monorepo
	uv run ruff check .

format:           ## Formata o código
	uv run ruff format .

test:             ## Roda todos os testes
	uv run pytest pipeline api

api:              ## Sobe a API local em http://localhost:8000
	uv run uvicorn app.main:app --reload --app-dir api

pipeline:         ## Pipeline completo: download -> normalização -> cruzamento
	uv run python -m radar_pipeline.pipeline

pipeline-amostra: ## Pipeline em modo amostra (1/10 do CNPJ — cabe em laptop)
	uv run python -m radar_pipeline.pipeline --amostra
