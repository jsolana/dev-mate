.PHONY: run
run:
	uvicorn main:app --reload --port 9000

.PHONY: format
format:
	black .
	isort .
