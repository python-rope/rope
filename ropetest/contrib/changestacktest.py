import unittest

import rope.base.change
import rope.base.history
import rope.contrib.changestack
from ropetest import testutils


class ChangeStackTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_change_stack(self):
        myfile = self.project.root.create_file("myfile.txt")
        myfile.write("1")
        stack = rope.contrib.changestack.ChangeStack(self.project)
        stack.push(rope.base.change.ChangeContents(myfile, "2"))
        self.assertEqual("2", myfile.read())
        stack.push(rope.base.change.ChangeContents(myfile, "3"))
        self.assertEqual("3", myfile.read())
        stack.pop_all()
        self.assertEqual("1", myfile.read())
        changes = stack.merged()
        self.project.do(changes)
        self.assertEqual("3", myfile.read())
