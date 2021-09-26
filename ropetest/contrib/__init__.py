import sys

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import ropetest.contrib.autoimporttest
import ropetest.contrib.changestacktest
import ropetest.contrib.codeassisttest
import ropetest.contrib.finderrorstest
import ropetest.contrib.findittest
import ropetest.contrib.fixmodnamestest
import ropetest.contrib.generatetest


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ropetest.contrib.generatetest.GenerateTest))
    result.addTests(ropetest.contrib.codeassisttest.suite())
    result.addTests(ropetest.contrib.autoimporttest.suite())
    result.addTests(ropetest.contrib.findittest.suite())
    result.addTests(
        unittest.makeSuite(ropetest.contrib.changestacktest.ChangeStackTest)
    )
    result.addTests(
        unittest.makeSuite(ropetest.contrib.fixmodnamestest.FixModuleNamesTest)
    )
    result.addTests(unittest.makeSuite(ropetest.contrib.finderrorstest.FindErrorsTest))
    return result


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    result = runner.run(suite())
    sys.exit(not result.wasSuccessful())
