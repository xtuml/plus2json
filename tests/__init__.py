import doctest
from . import test_pretty_print


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(test_pretty_print))
    return tests
