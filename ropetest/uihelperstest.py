import unittest
import Tkinter

from rope.uihelpers import EnhancedList, EnhancedListHandle
from rope.uihelpers import TreeViewer, TreeViewerHandle


class SampleListHandle(EnhancedListHandle):

    def __init__(self):
        pass

    def entry_to_string(self, integer_obj):
        return 'element ' + str(integer_obj)

class SampleTreeHandle(TreeViewerHandle):

    def __init__(self):
        pass

    def entry_to_string(self, integer_obj):
        return 'element ' + str(integer_obj)

    def get_children(self, integer_obj):
        return range(integer_obj)


class UIHelpersTest(unittest.TestCase):

    def setUp(self):
        super(UIHelpersTest, self).setUp()
        self.parent = Tkinter.Frame()

    def tearDown(self):
        self.parent.destroy()
        super(UIHelpersTest, self).tearDown()

    def test_enhanced_inserting_clearing(self):
        handle = SampleListHandle()
        enhanced_list = EnhancedList(self.parent, handle)
        enhanced_list.add_entry(1)
        enhanced_list.add_entry(2)
        self.assertEquals(2, enhanced_list.list.size())
        enhanced_list.clear()
        self.assertEquals(0, enhanced_list.list.size())

    def test_enhanced_list_to_string(self):
        handle = SampleListHandle()
        enhanced_list = EnhancedList(self.parent, handle)
        enhanced_list.add_entry(1)
        self.assertEquals('element 1', enhanced_list.list.get(0, 1)[0])

    def test_tree_view(self):
        handle = SampleTreeHandle()
        tree_viewer = TreeViewer(self.parent, handle)
        tree_viewer.add_entry(1)
        tree_viewer.add_entry(1)
        self.assertEquals('element 1', tree_viewer.list.get(0, 1)[0])


if __name__ == '__main__':
    unittest.main()
