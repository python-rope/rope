import unittest

import ropetest.projecttest
import ropetest.codeassisttest
import ropetest.codeanalyzetest
import ropetest.pycoretest
import ropetest.outlinetest
import ropetest.formattertest
import ropetest.refactortest
import ropetest.objectinfertest
import ropetest.runmodtest

import ropetest.ui.editortest
import ropetest.ui.fileeditortest
import ropetest.ui.coretest
import ropetest.ui.mockeditortest
import ropetest.ui.highlightertest
import ropetest.ui.searchertest
import ropetest.ui.statusbartest
import ropetest.ui.uihelperstest
import ropetest.ui.indentertest


def suite():
    result = unittest.TestSuite()
    result.addTests(ropetest.ui.mockeditortest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.fileeditortest.FileEditorTest))
    result.addTests(unittest.makeSuite(ropetest.ui.searchertest.SearchingTest))
    result.addTests(unittest.makeSuite(ropetest.ui.coretest.CoreTest))
    result.addTests(ropetest.ui.editortest.suite())
    result.addTests(ropetest.projecttest.suite())
    result.addTests(ropetest.ui.highlightertest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.indentertest.PythonCodeIndenterTest))
    result.addTests(ropetest.codeassisttest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.statusbartest.StatusBarTest))
    result.addTests(ropetest.codeanalyzetest.suite())
    result.addTests(ropetest.pycoretest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.uihelperstest.UIHelpersTest))
    result.addTests(unittest.makeSuite(ropetest.outlinetest.OutlineTest))
    result.addTests(unittest.makeSuite(ropetest.formattertest.FormatterTest))
    result.addTests(unittest.makeSuite(ropetest.refactortest.RefactoringTest))
    result.addTests(ropetest.objectinfertest.suite())
    result.addTests(ropetest.runmodtest.suite())
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
