import unittest

import ropeidetest.editortest
import ropeidetest.fileeditortest
import ropeidetest.coretest
import ropeidetest.mockeditortest
import ropeidetest.highlightertest
import ropeidetest.searchertest
import ropeidetest.statusbartest
import ropeidetest.uihelperstest
import ropeidetest.indentertest
import ropeidetest.filltest
import ropeidetest.formattertest
import ropeidetest.notestest
import ropeidetest.outlinetest
import ropeidetest.spellcheckertest
import ropeidetest.movementstest
import ropeidetest.sorttest


def suite():
    result = unittest.TestSuite()
    result.addTests(ropeidetest.mockeditortest.suite())
    result.addTests(unittest.makeSuite(ropeidetest.fileeditortest.FileEditorTest))
    result.addTests(unittest.makeSuite(ropeidetest.searchertest.SearchingTest))
    result.addTests(unittest.makeSuite(ropeidetest.coretest.CoreTest))
    result.addTests(ropeidetest.editortest.suite())
    result.addTests(ropeidetest.highlightertest.suite())
    result.addTests(unittest.makeSuite(ropeidetest.indentertest.PythonCodeIndenterTest))
    result.addTests(unittest.makeSuite(ropeidetest.statusbartest.StatusBarTest))
    result.addTests(unittest.makeSuite(ropeidetest.uihelperstest.UIHelpersTest))
    result.addTests(unittest.makeSuite(ropeidetest.filltest.FillTest))
    result.addTests(unittest.makeSuite(ropeidetest.formattertest.FormatterTest))
    result.addTests(unittest.makeSuite(ropeidetest.notestest.AnnotationsTest))
    result.addTests(unittest.makeSuite(ropeidetest.outlinetest.OutlineTest))
    result.addTests(ropeidetest.movementstest.suite())
    result.addTests(unittest.makeSuite(ropeidetest.sorttest.SortScopesTest))
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
