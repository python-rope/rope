import unittest

import ropetest.contrib.autoimporttest
import ropetest.contrib.codeassisttest
import ropetest.contrib.findittest
import ropetest.contrib.generatetest


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ropetest.contrib.generatetest.GenerateTest))
    result.addTests(ropetest.contrib.codeassisttest.suite())
    result.addTests(ropetest.contrib.autoimporttest.suite())
    result.addTests(ropetest.contrib.findittest.suite())
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
