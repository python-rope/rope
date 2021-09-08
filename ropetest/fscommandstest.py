from rope.base import fscommands


try:
    import unittest2 as unittest
except ImportError:
    import unittest


class ProjectTest(unittest.TestCase):
    def test_read_str_coding_doesnt_detect_encoding_if_encoding_keyword_in_python_code(
        self,
    ):
        result = fscommands.read_str_coding(
            b"""\
            class Test:
                def method(encoding='utf-16')
                    pass
        """
        )
        self.assertIsNone(result)

    def test_read_str_coding_detects_encoding_if_encoding_in_right_pattern(self,):
        result = fscommands.read_str_coding(
            b"""\
            #!/usr/bin/python
            # -*- coding: latin-1 -*-
            class Test:
                def method(encoding='utf-16')
                    pass
        """
        )
        self.assertEqual(result, "latin-1")
