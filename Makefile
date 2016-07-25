install:
	python setup.py install
test:
	make install
	python tests/rate_limit_test.py

