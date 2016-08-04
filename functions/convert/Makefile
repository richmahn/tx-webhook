# /usr/local/bin must be in PATH
SHELL := /bin/bash
test := functions/convert/test/
usfm ta obs:
	cd ../.. ; apex deploy
	cd ../.. ; apex invoke convert -D --logs < $(test)$@.json

build:  
	cd ../.. ; apex build convert > functions/convert/convert.zip

