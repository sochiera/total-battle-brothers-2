PY=python3
VENV=.venv
PYBIN=$(VENV)/bin/python3

.PHONY: venv install run test clean

venv: $(VENV)/bin/python3
	@if [ ! -x $(VENV)/bin/pip ]; then \
		echo "(python3-venv/ensurepip is missing - install it and recreate .venv)"; \
		echo; echo "    sudo apt install python3-venv"; \
		echo "    rm -rf .venv && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; \
		exit 1; \
	fi
	$(VENV)/bin/pip install -q -r requirements.txt

$(VENV)/bin/python3:
	@if $(PY) -m venv --help >/dev/null 2>&1 && $(PY) -c "import ensurepip" 2>/dev/null; then \
		$(PY) -m venv $(VENV); \
	else \
		echo "(python3-venv/ensurepip is missing - install it, or run: make run2)"; \
		echo; echo "    sudo apt install python3-venv"; \
		echo "    rm -rf .venv && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; \
		exit 1; \
	fi

install: venv

run: venv
	$(PYBIN) -m tbb

test: venv
	$(PYBIN) -m pytest -q

clean:
	rm -rf $(VENV) saves __pycache__ tbb/__pycache__ tbb/rules/__pycache__ tbb/app/__pycache__ tests/__pycache__ .pytest_cache
