import os
import unittest
from textwrap import dedent

from rope.base import exceptions
from ropetest import testutils


class PythonFileRunnerTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def make_sample_python_file(self, file_path, get_text_function_source=None):
        self.project.root.create_file(file_path)
        file = self.project.get_resource(file_path)
        if not get_text_function_source:
            get_text_function_source = "def get_text():\n    return 'run'\n\n"
        file_content = (
            get_text_function_source + "output = open('output.txt', 'w')\n"
            "output.write(get_text())\noutput.close()\n"
        )
        file.write(file_content)

    def get_output_file_content(self, file_path):
        try:
            output_path = ""
            last_slash = file_path.rfind("/")
            if last_slash != -1:
                output_path = file_path[0 : last_slash + 1]
            file = self.project.get_resource(output_path + "output.txt")
            return file.read()
        except exceptions.ResourceNotFoundError:
            return ""

    def test_making_runner(self):
        file_path = "sample.py"
        self.make_sample_python_file(file_path)
        file_resource = self.project.get_resource(file_path)
        runner = self.pycore.run_module(file_resource)
        runner.wait_process()
        self.assertEqual("run", self.get_output_file_content(file_path))

    def test_passing_arguments(self):
        file_path = "sample.py"
        function_source = dedent("""\
            import sys
            def get_text():
                return str(sys.argv[1:])
        """)
        self.make_sample_python_file(file_path, function_source)
        file_resource = self.project.get_resource(file_path)
        runner = self.pycore.run_module(file_resource, args=["hello", "world"])
        runner.wait_process()
        self.assertTrue(
            self.get_output_file_content(file_path).endswith("['hello', 'world']")
        )

    def test_passing_arguments_with_spaces(self):
        file_path = "sample.py"
        function_source = dedent("""\
            import sys
            def get_text():
                return str(sys.argv[1:])
        """)
        self.make_sample_python_file(file_path, function_source)
        file_resource = self.project.get_resource(file_path)
        runner = self.pycore.run_module(file_resource, args=["hello world"])
        runner.wait_process()
        self.assertTrue(
            self.get_output_file_content(file_path).endswith("['hello world']")
        )

    def test_killing_runner(self):
        file_path = "sample.py"
        code = dedent("""\
            def get_text():
                import time
                time.sleep(1)
                return 'run'
        """)
        self.make_sample_python_file(
            file_path,
            code,
        )
        file_resource = self.project.get_resource(file_path)
        runner = self.pycore.run_module(file_resource)
        runner.kill_process()
        self.assertEqual("", self.get_output_file_content(file_path))

    def test_running_nested_files(self):
        self.project.root.create_folder("src")
        file_path = "src/sample.py"
        self.make_sample_python_file(file_path)
        file_resource = self.project.get_resource(file_path)
        runner = self.pycore.run_module(file_resource)
        runner.wait_process()
        self.assertEqual("run", self.get_output_file_content(file_path))

    def test_setting_process_input(self):
        file_path = "sample.py"
        code = dedent("""\
            def get_text():
                import sys
                return sys.stdin.readline()
        """)
        self.make_sample_python_file(file_path, code)
        temp_file_name = "processtest.tmp"
        try:
            temp_file = open(temp_file_name, "w")
            temp_file.write("input text\n")
            temp_file.close()
            file_resource = self.project.get_resource(file_path)
            stdin = open(temp_file_name)
            runner = self.pycore.run_module(file_resource, stdin=stdin)
            runner.wait_process()
            stdin.close()
            self.assertEqual("input text\n", self.get_output_file_content(file_path))
        finally:
            os.remove(temp_file_name)

    def test_setting_process_output(self):
        file_path = "sample.py"
        code = dedent("""\
            def get_text():
                print('output text')
                return 'run'
        """)
        self.make_sample_python_file(file_path, code)
        temp_file_name = "processtest.tmp"
        try:
            file_resource = self.project.get_resource(file_path)
            stdout = open(temp_file_name, "w")
            runner = self.pycore.run_module(file_resource, stdout=stdout)
            runner.wait_process()
            stdout.close()
            temp_file = open(temp_file_name)
            self.assertEqual("output text\n", temp_file.read())
            temp_file.close()
        finally:
            os.remove(temp_file_name)

    def test_setting_pythonpath(self):
        src = self.project.root.create_folder("src")
        src.create_file("sample.py")
        src.get_child("sample.py").write("def f():\n    pass\n")
        self.project.root.create_folder("test")
        file_path = "test/test.py"
        code = dedent("""\
            def get_text():
                import sample
                sample.f()
                return'run'
        """)
        self.make_sample_python_file(file_path, code)
        file_resource = self.project.get_resource(file_path)
        runner = self.pycore.run_module(file_resource)
        runner.wait_process()
        self.assertEqual("run", self.get_output_file_content(file_path))

    def test_making_runner_when_doi_is_disabled(self):
        self.project.set("enable_doi", False)
        file_path = "sample.py"
        self.make_sample_python_file(file_path)
        file_resource = self.project.get_resource(file_path)
        runner = self.pycore.run_module(file_resource)
        runner.wait_process()
        self.assertEqual("run", self.get_output_file_content(file_path))
