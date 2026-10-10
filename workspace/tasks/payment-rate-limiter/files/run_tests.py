import sys
import unittest

suite = unittest.defaultTestLoader.discover(".", pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
if result.testsRun == 0:
    print("Не найдено ни одного теста: нужны файлы test_*.py в корне или в папках с __init__.py", file=sys.stderr)
    sys.exit(1)
sys.exit(0 if result.wasSuccessful() else 1)
