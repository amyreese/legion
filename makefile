.venv:
	python -m venv .venv
	source .venv/bin/activate && make setup dev
	echo 'run `source .venv/bin/activate` to develop legion'

venv: .venv

setup:
	python -m pip install -Ur requirements-dev.txt

dev:
	flit install --symlink

release: lint test clean
	flit publish

format:
	python -m usort format legion
	python -m black legion

lint:
	python -m usort check legion
	python -m black --check legion

test:
	python -m mypy legion/*.py

clean:
	rm -rf build dist html README MANIFEST *.egg-info

distclean: clean
	rm -rf .venv
