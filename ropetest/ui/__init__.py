import unittest

import ropetest.ui.editortest
import ropetest.ui.fileeditortest
import ropetest.ui.coretest
import ropetest.ui.mockeditortest
import ropetest.ui.highlightertest
import ropetest.ui.searchertest
import ropetest.ui.statusbartest
import ropetest.ui.uihelperstest
import ropetest.ui.filltest


def suite():
    result = unittest.TestSuite()
    result.addTests(ropetest.ui.mockeditortest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.fileeditortest.FileEditorTest))
    result.addTests(unittest.makeSuite(ropetest.ui.searchertest.SearchingTest))
    result.addTests(unittest.makeSuite(ropetest.ui.coretest.CoreTest))
    result.addTests(ropetest.ui.editortest.suite())
    result.addTests(ropetest.ui.highlightertest.suite())
    result.addTests(unittest.makeSuite(ropetest.ui.indentertest.PythonCodeIndenterTest))
    result.addTests(unittest.makeSuite(ropetest.ui.statusbartest.StatusBarTest))
    result.addTests(unittest.makeSuite(ropetest.ui.uihelperstest.UIHelpersTest))
    result.addTests(unittest.makeSuite(ropetest.ui.filltest.FillTest))
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
