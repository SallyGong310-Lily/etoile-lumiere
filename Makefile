.PHONY: install login etoile lumiere apps test clean

install:
	./scripts/install.sh

login:
	.venv/bin/python -m pytok.accounts.cli login --username "$${TIKTOK_ACCOUNT:-$$USER}" --manual-login

etoile:
	./scripts/etoile_launcher.sh

lumiere:
	./scripts/lumiere_launcher.sh

apps:
	./scripts/build_app.sh

test:
	.venv/bin/python -m compileall -q src
	@echo "syntax OK"

clean:
	rm -rf dist build __pycache__ src/__pycache__
