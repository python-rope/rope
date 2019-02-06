import sys
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import ropetest.projecttest
import ropetest.codeanalyzetest
import ropetest.doatest
import ropetest.type_hinting_test
import ropetest.pycoretest
import ropetest.pyscopestest
import ropetest.objectinfertest
import ropetest.objectdbtest
import ropetest.advanced_oi_test
import ropetest.runmodtest
import ropetest.builtinstest
import ropetest.historytest
import ropetest.simplifytest

import ropetest.contrib
import ropetest.refactor


def suite():
    result = unittest.TestSuite()
    result.addTests(ropetest.projecttest.suite())
    result.addTests(ropetest.codeanalyzetest.suite())
    result.addTests(ropetest.doatest.suite())
    result.addTests(ropetest.type_hinting_test.suite())
    result.addTests(ropetest.pycoretest.suite())
    result.addTests(ropetest.pyscopestest.suite())
    result.addTests(ropetest.objectinfertest.suite())
    result.addTests(ropetest.objectdbtest.suite())
    result.addTests(ropetest.advanced_oi_test.suite())
    result.addTests(ropetest.runmodtest.suite())
    result.addTests(ropetest.builtinstest.suite())
    result.addTests(ropetest.historytest.suite())
    result.addTests(ropetest.simplifytest.suite())

    result.addTests(ropetest.refactor.suite())
    result.addTests(ropetest.contrib.suite())

    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    result = runner.run(suite())
    sys.exit(not result.wasSuccessful())
