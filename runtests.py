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


if __name__ == '__main__':
    result = unittest.TestSuite()
    result.addTests(ropetest.mockeditortest.suite())
    result.addTests(unittest.makeSuite(ropetest.fileeditortest.FileEditorTest))
    result.addTests(unittest.makeSuite(ropetest.searchingtest.SearchingTest))
    result.addTests(unittest.makeSuite(ropetest.coretest.CoreTest))
    result.addTests(unittest.makeSuite(ropetest.editortest.GraphicalEditorTest))
    result.addTests(ropetest.projecttest.suite())
    result.addTests(unittest.makeSuite(ropetest.highlighttest.HighlightTest))
    result.addTests(unittest.makeSuite(ropetest.indentertest.PythonCodeIndenterTest))
    result.addTests(ropetest.codeassisttest.suite())
    result.addTests(unittest.makeSuite(ropetest.statusbartest.StatusBarTest))
    result.addTests(unittest.makeSuite(ropetest.codeanalyzetest.StatementRangeFinderTest))
    result.addTests(ropetest.pycoretest.suite())
    runner = unittest.TextTestRunner()
    runner.run(result)
