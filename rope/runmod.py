import os
import subprocess
import sys

class PythonFileRunner(object):
    """A class for running python project files"""

    def __init__(self, file_, stdin=None, stdout=None):
        self.file = file_
        file_path = self.file._get_real_path()
        env = {}
        env.update(os.environ)
        source_folders = []
        for folder in file_.get_project().get_pycore().get_source_folders():
            source_folders.append(os.path.abspath(folder._get_real_path()))
        env['PYTHONPATH'] = env.get('PYTHONPATH', '') + os.pathsep + \
                            os.pathsep.join(source_folders)
        self.process = subprocess.Popen(executable=sys.executable,
                                        args=(sys.executable, self.file.get_name()),
                                        cwd=os.path.split(file_path)[0], stdin=stdin,
                                        stdout=stdout, stderr=stdout, env=env)

    def wait_process(self):
        """Wait for the process to finish"""
        self.process.wait()

    def kill_process(self):
        """Stop the process. This does not work on windows."""
        os.kill(self.process.pid, 9)

