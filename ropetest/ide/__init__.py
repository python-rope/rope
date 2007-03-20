import unittest

import ropetest.ide.generatetest
import ropetest.ide.codeassisttest
import ropetest.ide.formattertest
import ropetest.ide.notestest
import ropetest.ide.outlinetest


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ropetest.ide.generatetest.GenerateTest))
    result.addTests(ropetest.ide.codeassisttest.suite())
    result.addTests(unittest.makeSuite(ropetest.ide.formattertest.FormatterTest))
    result.addTests(unittest.makeSuite(ropetest.ide.notestest.AnnotationsTest))
    result.addTests(unittest.makeSuite(ropetest.ide.outlinetest.OutlineTest))
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
