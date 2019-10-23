build_r:
	cp LICENSE clients/r-client
	R CMD build clients/r-client

build_py:
	cp LICENSE clients/py-client
	cd clients/py-client && python3 setup.py sdist
