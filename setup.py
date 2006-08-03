import os
from distutils.core import setup

def make_scripts():
    if not os.path.exists('scripts'):
        os.mkdir('scripts')
    rope_py_text = file('rope.py').read()
    rope_script_file = file('scripts/rope', 'w')
    rope_script_file.write(rope_py_text)
    rope_script_file.close()

make_scripts()

setup(name='rope',
      version='0.2',
      description='A Python IDE ...',
      author='Ali Gholami Rudi',
      author_email='aligrudi@users.sourceforge.net',
      url='http://rope.sf.net/',
      packages=['rope', 'rope.ui'],
      scripts=['scripts/rope'])

