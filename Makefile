.PHONY: setup lint format test api pipeline

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

pipeline:         ## Pipeline completo de dados (P1.9 — ainda não implementado)
	@echo "TODO(P1.9): download -> normalização -> cruzamento -> carga"
	@exit 1
