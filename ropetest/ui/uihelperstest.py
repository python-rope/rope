import unittest
import Tkinter

from rope.ui.uihelpers import EnhancedList, EnhancedListHandle
from rope.ui.uihelpers import TreeView, TreeViewHandle


class SampleListHandle(EnhancedListHandle):

    def __init__(self):
        pass

    def entry_to_string(self, integer_obj):
        return 'element ' + str(integer_obj)

class SampleTreeHandle(TreeViewHandle):

    def __init__(self):
        pass

    def entry_to_string(self, string_obj):
        return 'element ' + str(string_obj)

    def get_children(self, string_obj):
        if len(string_obj) > 2:
            return []
        return [string_obj + str(i) for i in range(3)]


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
        tree_viewer = TreeView(self.parent, handle)
        tree_viewer.add_entry('a')
        self.assertTrue(tree_viewer.list.get(0, 1)[0].endswith('element a'))

    def test_tree_view_expanding(self):
        handle = SampleTreeHandle()
        tree_viewer = TreeView(self.parent, handle)
        tree_viewer.add_entry('a')
        tree_viewer.expand(0)
        self.assertEquals(4, tree_viewer.list.size())
        self.assertTrue(tree_viewer.list.get(0, 1)[0].endswith('element a'))
        self.assertTrue(tree_viewer.list.get(1, 4)[0].endswith('element a0'))
        self.assertTrue(tree_viewer.list.get(1, 4)[1].endswith('element a1'))
        self.assertTrue(tree_viewer.list.get(1, 4)[2].endswith('element a2'))

    def test_tree_view_multi_expanding(self):
        handle = SampleTreeHandle()
        tree_viewer = TreeView(self.parent, handle)
        tree_viewer.add_entry('a')
        tree_viewer.expand(0)
        tree_viewer.expand(0)
        self.assertEquals(4, tree_viewer.list.size())

    def test_tree_view_shrinking(self):
        handle = SampleTreeHandle()
        tree_viewer = TreeView(self.parent, handle)
        tree_viewer.add_entry('a')
        tree_viewer.expand(0)
        self.assertEquals(4, tree_viewer.list.size())
        tree_viewer.collapse(0)
        self.assertEquals(1, tree_viewer.list.size())
        self.assertTrue(tree_viewer.list.get(0, 1)[0].endswith('element a'))

    def test_expansion_signs(self):
        handle = SampleTreeHandle()
        tree_viewer = TreeView(self.parent, handle)
        tree_viewer.add_entry('a')
        self.assertEquals('+ element a', tree_viewer.list.get(0, 1)[0])
        tree_viewer.expand(0)
        self.assertEquals('- element a', tree_viewer.list.get(0, 1)[0])
        tree_viewer.collapse(0)
        self.assertEquals('+ element a', tree_viewer.list.get(0, 1)[0])

    def test_expansion_signs_for_leaves(self):
        handle = SampleTreeHandle()
        tree_viewer = TreeView(self.parent, handle)
        tree_viewer.add_entry('a00')
        self.assertEquals('  element a00', tree_viewer.list.get(0, 1)[0])
        tree_viewer.expand(0)
        self.assertEquals('  element a00', tree_viewer.list.get(0, 1)[0])

    
if __name__ == '__main__':
    unittest.main()

