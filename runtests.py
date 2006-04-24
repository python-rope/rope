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

if __name__ == '__main__':
    result = unittest.TestSuite()
    result.addTests(ropetest.mockeditortest.suite())
    result.addTests(unittest.makeSuite(ropetest.fileeditortest.FileEditorTest))
    result.addTests(unittest.makeSuite(ropetest.searchingtest.SearchingTest))
    result.addTests(unittest.makeSuite(ropetest.coretest.CoreTest))
    result.addTests(unittest.makeSuite(ropetest.editortest.GraphicalEditorTest))
    result.addTests(unittest.makeSuite(ropetest.projecttest.ProjectTest))
    result.addTests(unittest.makeSuite(ropetest.projecttest.FileFinderTest))
    result.addTests(unittest.makeSuite(ropetest.projecttest.TestPythonFileRunner))
    result.addTests(unittest.makeSuite(ropetest.highlighttest.HighlightTest))
    result.addTests(unittest.makeSuite(ropetest.indentertest.PythonCodeIndenterTest))
    runner = unittest.TextTestRunner()
    runner.run(result)
