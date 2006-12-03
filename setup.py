import glob
import os
import shutil
from distutils.core import setup

import rope

def make_temps():
    if not os.path.exists('scripts'):
        os.mkdir('scripts')
    shutil.copy('rope.py', 'scripts/rope')
    # copying docs
    if not os.path.exists('rope/docs'):
        os.mkdir('rope/docs')
    docs = ['README.txt', 'COPYING']
    docs.extend(glob.glob('docs/user/*.txt'))
    docs.extend(glob.glob('docs/dev/*.txt'))
    docs.extend(glob.glob('docs/*.txt'))
    for name in docs:
        shutil.copy(name, 'rope/docs/')

def remove_temps():
    if os.path.exists('scripts'):
        shutil.rmtree('scripts')
    if os.path.exists('rope/docs'):
        shutil.rmtree('rope/docs')

make_temps()

classifiers=['Development Status :: 3 - Alpha',
             'Operating System :: OS Independent',
             'Environment :: X11 Applications',
             'Environment :: Win32 (MS Windows)',
             # Have not been tested on MacOS
             # 'Environment :: MacOS X',
             'Intended Audience :: Developers',
             'License :: OSI Approved :: GNU General Public License (GPL)',
             'Natural Language :: English',
             'Programming Language :: Python',
             'Topic :: Software Development',
             'Topic :: Text Editors :: Integrated Development Environments (IDE)']

long_description = """
Rope is a python refactoring IDE and library.
"""

setup(name='rope',
      version=rope.VERSION,
      description='a python refactoring IDE...',
      long_description=long_description,
      author='Ali Gholami Rudi',
      author_email='aligrudi@users.sourceforge.net',
      url='http://rope.sf.net/',
      packages=['rope', 'rope.base', 'rope.base.oi', 'rope.refactor',
                'rope.ide', 'rope.ui'],
      package_data={'rope': ['docs/COPYING', 'docs/*.txt']},
      scripts=['scripts/rope'],
      classifiers=classifiers)

remove_temps()
