import unittest

import ropetest.projecttest
import ropetest.codeassisttest
import ropetest.codeanalyzetest
import ropetest.pycoretest
import ropetest.pyscopestest
import ropetest.outlinetest
import ropetest.formattertest
import ropetest.objectinfertest
import ropetest.runmodtest
import ropetest.builtintest
import ropetest.historytest


def suite():
    result = unittest.TestSuite()
    result.addTests(ropetest.projecttest.suite())
    result.addTests(ropetest.codeassisttest.suite())
    result.addTests(ropetest.codeanalyzetest.suite())
    result.addTests(ropetest.pycoretest.suite())
    result.addTests(ropetest.pyscopestest.suite())
    result.addTests(unittest.makeSuite(ropetest.outlinetest.OutlineTest))
    result.addTests(unittest.makeSuite(ropetest.formattertest.FormatterTest))
    result.addTests(ropetest.objectinfertest.suite())
    result.addTests(ropetest.runmodtest.suite())
    result.addTests(unittest.makeSuite(ropetest.builtintest.BuiltinTypesTest))
    result.addTests(unittest.makeSuite(ropetest.historytest.HistoryTest))
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
