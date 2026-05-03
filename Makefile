.PHONY: install verify test seed build deploy deploy-prod clean

install:
	pip install -r requirements-dev.txt

verify:
	python scripts/verify_code.py src/

test:
	pytest tests/ -v

seed:
	python scripts/seed_db.py

build:
	sam build

deploy:
	sam deploy --stack-name mcp-hub-dev --parameter-overrides Stage=dev

deploy-prod:
	sam deploy --stack-name mcp-hub-prod --parameter-overrides Stage=prod

clean:
	rm -rf .aws-sam .build .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
