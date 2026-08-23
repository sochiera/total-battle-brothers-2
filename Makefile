PY=python3
VENV=.venv
PYBIN=$(VENV)/bin/python3
# venv attempts normal ensurepip, --without-pip, and pip3 --python.  The test
# target delegates to run.sh so a capable system python3 remains a fallback.

.PHONY: venv install run test clean

venv: $(VENV)/bin/python3
	@if [ -x $(VENV)/bin/pip ]; then \
		$(VENV)/bin/pip install -q -r requirements.txt || true; \
	else \
		pip3 --python $(VENV) install -q -r requirements.txt || true; \
	fi

$(VENV)/bin/python3:
	@if ! $(PY) -m venv $(VENV); then \
		$(PY) -m venv --without-pip $(VENV) || true; \
	fi

install: venv

run:
	./run.sh

test:
	./run.sh --test

clean:
	rm -rf $(VENV) saves __pycache__ tbb/__pycache__ tbb/rules/__pycache__ tbb/app/__pycache__ tests/__pycache__ .pytest_cache
