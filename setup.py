import os
import shutil
from distutils.core import setup

import rope


def make_scripts():
    if not os.path.exists('scripts'):
        os.mkdir('scripts')
    shutil.copy('rope.py', 'scripts/rope')


make_scripts()

setup(name='rope',
      version=rope.VERSION,
      description='A Python IDE ...',
      author='Ali Gholami Rudi',
      author_email='aligrudi@users.sourceforge.net',
      url='http://rope.sf.net/',
      packages=['rope', 'rope.base', 'rope.refactor', 'rope.ide', 'rope.ui'],
      scripts=['scripts/rope'])

