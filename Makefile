.PHONY: setup backend frontend test lint build

setup:
	python3 -m venv simulation/venv
	simulation/venv/bin/pip install -r simulation/requirements-dev.txt
	cd frontend && npm install

backend:
	cd simulation && venv/bin/python app.py

frontend:
	cd frontend && npm run dev

test:
	cd simulation && venv/bin/python -m pytest -q

lint:
	cd frontend && npm run lint && npx tsc --noEmit

build:
	cd frontend && npm run build
