start:
	cat tests/test_init.in | python3 main.py --init > result && python3 tests/validate.py tests/test_init.in result tests/test_init.out 
	cat tests/test.in | python3 main.py > result && python3 tests/validate.py tests/test.in result tests/test.out 
