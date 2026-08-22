PY=python3
VENV=.venv
PYBIN=$(VENV)/bin/python3

.PHONY: venv install run test clean

venv: $(VENV)/bin/python3
	@if [ -x $(VENV)/bin/pip ]; then \
		$(VENV)/bin/pip install -q -r requirements.txt; \
	else \
		pip3 --python $(VENV) install -q -r requirements.txt; \
	fi

$(VENV)/bin/python3:
	@if ! $(PY) -m venv $(VENV); then \
		$(PY) -m venv --without-pip $(VENV); \
	fi

install: venv

run: venv
	$(PYBIN) -m tbb

test: venv
	$(PYBIN) -m pytest -q

clean:
	rm -rf $(VENV) saves __pycache__ tbb/__pycache__ tbb/rules/__pycache__ tbb/app/__pycache__ tests/__pycache__ .pytest_cache
