import unittest
import ropetest
import ropetest.editortest
import ropetest.fileeditortest
import ropetest.coretest
import ropetest.mockeditortest
import ropetest.projecttest
import ropetest.highlighttest
import ropetest.searchingtest
import ropetest.indentertest
import ropetest.codeassisttest
import ropetest.statusbartest
import ropetest.codeanalyzetest
import ropetest.pycoretest
import ropetest.uihelperstest
import ropetest.outlinetest
import ropetest.formattertest
import ropetest.refactoringtest


if __name__ == '__main__':
    result = unittest.TestSuite()
    result.addTests(ropetest.mockeditortest.suite())
    result.addTests(unittest.makeSuite(ropetest.fileeditortest.FileEditorTest))
    result.addTests(unittest.makeSuite(ropetest.searchingtest.SearchingTest))
    result.addTests(unittest.makeSuite(ropetest.coretest.CoreTest))
    result.addTests(unittest.makeSuite(ropetest.editortest.GraphicalEditorTest))
    result.addTests(ropetest.projecttest.suite())
    result.addTests(ropetest.highlighttest.suite())
    result.addTests(unittest.makeSuite(ropetest.indentertest.PythonCodeIndenterTest))
    result.addTests(ropetest.codeassisttest.suite())
    result.addTests(unittest.makeSuite(ropetest.statusbartest.StatusBarTest))
    result.addTests(ropetest.codeanalyzetest.suite())
    result.addTests(ropetest.pycoretest.suite())
    result.addTests(unittest.makeSuite(ropetest.uihelperstest.UIHelpersTest))
    result.addTests(unittest.makeSuite(ropetest.outlinetest.OutlineTest))
    result.addTests(unittest.makeSuite(ropetest.formattertest.FormatterTest))
    result.addTests(unittest.makeSuite(ropetest.refactoringtest.RefactoringTest))
    runner = unittest.TextTestRunner()
    runner.run(result)
