import unittest

import ropetest
import ropetest.refactor
import ropetest.ui


def suite():
    result = unittest.TestSuite()
    result.addTests(ropetest.suite())
    result.addTests(ropetest.refactor.suite())
    result.addTests(ropetest.ui.suite())
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
