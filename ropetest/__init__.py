import unittest

import ropetest.projecttest
import ropetest.codeanalyzetest
import ropetest.pycoretest
import ropetest.pyscopestest
import ropetest.objectinfertest
import ropetest.objectdbtest
import ropetest.advanced_oi_test
import ropetest.runmodtest
import ropetest.builtinstest
import ropetest.historytest
import ropetest.simplifytest


def suite():
    result = unittest.TestSuite()
    result.addTests(ropetest.projecttest.suite())
    result.addTests(ropetest.codeanalyzetest.suite())
    result.addTests(ropetest.pycoretest.suite())
    result.addTests(ropetest.pyscopestest.suite())
    result.addTests(ropetest.objectinfertest.suite())
    result.addTests(ropetest.objectdbtest.suite())
    result.addTests(ropetest.advanced_oi_test.suite())
    result.addTests(ropetest.runmodtest.suite())
    result.addTests(ropetest.builtinstest.suite())
    result.addTests(ropetest.historytest.suite())
    result.addTests(ropetest.simplifytest.suite())
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
