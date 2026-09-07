.PHONY: install ingest run test eval demo docker

install:
	pip install -r requirements.txt

ingest:
	python scripts/ingest_seed_data.py

run:
	uvicorn src.sentinel.api.main:app --reload --port 8000

test:
	pytest tests/ -v

eval:
	python -m src.sentinel.eval.run_eval

demo:
	python scripts/demo_query.py

docker:
	docker compose up --build
