import os.path
import sys

import Tkinter

import rope.ui.core
from rope.ui.extension import SimpleAction
from rope.ui.menubar import MenuAddress
from rope.base import project


def show_about_dialog(context):
    toplevel = Tkinter.Toplevel()
    toplevel.title('About Rope')
    text = rope.__doc__ + ' ...\n' + \
           'version ' + rope.VERSION + '\n\n' + \
           'Copyright (C) 2006-2007 Ali Gholami Rudi\n\n' + \
           'This program is free software; you can redistribute it and/or modify it\n' + \
           'under the terms of GNU General Public License as published by the \n' + \
           'Free Software Foundation; either version 2 of the license, or (at your \n' + \
           'opinion) any later version.\n\n' + \
           'This program is distributed in the hope that it will be useful,\n' + \
           'but WITHOUT ANY WARRANTY; without even the implied warranty of\n' + \
           'MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n' + \
           'GNU General Public License for more details.\n'
    label = Tkinter.Label(toplevel, text=text, height=16, width=70,
                          justify=Tkinter.LEFT, relief=Tkinter.GROOVE)
    def ok():
        toplevel.destroy()
    def show_gpl():
        show_copying(context)
        toplevel.destroy()
    label.grid(row=0, column=0, columnspan=2)
    ok_button = Tkinter.Button(toplevel, text='OK', command=ok, width=20)
    gpl_button = Tkinter.Button(toplevel, text='Show GNU GPL',
                                command=show_gpl, width=20)
    gpl_button.grid(row=1, column=0)
    ok_button.grid(row=1, column=1)
    ok_button.focus_set()

def show_doc(context, name):
    rope_package = (os.path.dirname(sys.modules['rope'].__file__))
    # Checking whether rope is installed or not
    no_project = project.get_no_project()
    if 'docs' in os.listdir(rope_package):
        root = rope_package
        resource = no_project.get_resource(root + '/docs/' + name.split('/')[-1])
    else:
        root = os.path.dirname(rope_package)
        resource = no_project.get_resource(root + '/' + name)
    editor_manager = context.get_core().get_editor_manager()
    editor_manager.get_resource_editor(resource, readonly=True)

def show_readme(context):
    show_doc(context, 'README.txt')

def show_features(context):
    show_doc(context, 'docs/index.txt')

def show_overview(context):
    show_doc(context, 'docs/user/overview.txt')

def show_tutorial(context):
    show_doc(context, 'docs/user/tutorial.txt')

def show_contributing(context):
    show_doc(context, 'docs/dev/contributing.txt')

def show_library(context):
    show_doc(context, 'docs/dev/library.txt')

def show_copying(context):
    show_doc(context, 'COPYING')


core = rope.ui.core.Core.get_core()
core.add_menu_cascade(MenuAddress(['Help'], 'h'), ['all', 'none'])
actions = []

actions.append(SimpleAction('readme', show_readme, 'C-h r',
                            MenuAddress(['Help', 'Readme'], 'r')))
actions.append(SimpleAction('features', show_features, 'C-h f',
                            MenuAddress(['Help', 'Features'], 'f')))
actions.append(SimpleAction('overview', show_overview, 'C-h o',
                            MenuAddress(['Help', 'Overview'], 'o')))
actions.append(SimpleAction('tutorial', show_tutorial, 'C-h t',
                            MenuAddress(['Help', 'Tutorial'], 't')))

actions.append(SimpleAction('contributing', show_contributing, 'C-h c',
                            MenuAddress(['Help', 'Contributing'], 'n', 1)))
actions.append(SimpleAction('library', show_library, 'C-h l',
                            MenuAddress(['Help', 'Using Rope As A Library'],
                                        'l', 1)))

actions.append(SimpleAction('about', show_about_dialog, 'C-h a',
                            MenuAddress(['Help', 'About Rope'], 'a', 2)))

for action in actions:
    core.register_action(action)
