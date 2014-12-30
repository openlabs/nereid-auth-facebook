test: test-sqlite test-flake8

test-sqlite: install-dependencies
	python setup.py test

test-flake8:
	pip install flake8
	flake8 .

install-dependencies:
	CFLAGS=-O0 pip install lxml
	pip install -r dev_requirements.txt
