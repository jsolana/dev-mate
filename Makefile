.PHONY: run
run:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

.PHONY: format
format:
	black .
	isort .
