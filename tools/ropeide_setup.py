import glob
import os
import shutil
from distutils.core import setup

import rope


def make_temps():
    if not os.path.exists('scripts'):
        os.mkdir('scripts')
    shutil.copy('ropeide.py', 'scripts/ropeide')
    # copying docs
    if not os.path.exists('ropeide/docs'):
        os.mkdir('ropeide/docs')
    docs = ['README.txt', 'COPYING']
    docs.extend(glob.glob('docs/*.txt'))
    for name in docs:
        shutil.copy(name, 'ropeide/docs/')

def remove_temps():
    if os.path.exists('scripts'):
        shutil.rmtree('scripts')
    if os.path.exists('ropeide/docs'):
        shutil.rmtree('ropeide/docs')

classifiers=[
    'Development Status :: 4 - Beta',
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

def get_long_description():
    lines = open('README.txt').read().splitlines(False)
    end = lines.index('Getting Started')
    return '\n' + '\n'.join(lines[:end]) + '\n'

make_temps()
try:
    setup(name='ropeide',
          version=rope.VERSION,
          description='a python refactoring IDE...',
          long_description=get_long_description(),
          author='Ali Gholami Rudi',
          author_email='aligrudi@users.sourceforge.net',
          url='http://rope.sf.net/',
          packages=['ropeide'],
          package_data={'ropeide': ['docs/COPYING', 'docs/*.txt']},
          scripts=['scripts/ropeide'],
          license='GNU GPL',
          classifiers=classifiers)
finally:
    remove_temps()
