import unittest

import ropetest.ui.editortest
import ropetest.ui.fileeditortest
import ropetest.ui.coretest
import ropetest.ui.mockeditortest
import ropetest.ui.highlighttest
import ropetest.ui.searchingtest
import ropetest.ui.statusbartest
import ropetest.ui.uihelperstest
import ropetest.ui.indentertest
import ropetest.projecttest
import ropetest.codeassisttest
import ropetest.codeanalyzetest
import ropetest.pycoretest
import ropetest.outlinetest
import ropetest.formattertest
import ropetest.refactoringtest


if __name__ == '__main__':
    result = unittest.TestSuite()
    result.addTests(ropetest.ui.mockeditortest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.fileeditortest.FileEditorTest))
    result.addTests(unittest.makeSuite(ropetest.ui.searchingtest.SearchingTest))
    result.addTests(unittest.makeSuite(ropetest.ui.coretest.CoreTest))
    result.addTests(ropetest.ui.editortest.suite())
    result.addTests(ropetest.projecttest.suite())
    result.addTests(ropetest.ui.highlighttest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.indentertest.PythonCodeIndenterTest))
    result.addTests(ropetest.codeassisttest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.statusbartest.StatusBarTest))
    result.addTests(ropetest.codeanalyzetest.suite())
    result.addTests(ropetest.pycoretest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.uihelperstest.UIHelpersTest))
    result.addTests(unittest.makeSuite(ropetest.outlinetest.OutlineTest))
    result.addTests(unittest.makeSuite(ropetest.formattertest.FormatterTest))
    result.addTests(unittest.makeSuite(ropetest.refactoringtest.RefactoringTest))
    runner = unittest.TextTestRunner()
    runner.run(result)
