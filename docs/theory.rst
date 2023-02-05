.. rst3: filename: docs/theory

==========================
Rope's Theory of Operation
==========================

This document describes how Rope does type inference.

.. contents:: Table of Contents

Notes from YouTube video
++++++++++++++++++++++++

.. https://youtu.be/NvV5OrVk24c

Project: Tree of directories and files.
         Instantiate a Project with a directory.
         
With a Project you can:
- walk the resources (File or Directory).
- get the children of a resource and continue walking.

Prefs: Dictionary of keys to values (settings).
- .ropeproject is reflected directly into the Prefs class.

Resources: (File or Directory).
Typical use:
- Walk the resource to find specific resources you want to work with.
- Apply refactoring to specific resources.

=== How to refactor.

1. Create a Rename object.
   ren = Rename(project, resource, offset)
   
2. Create the changes object.
   changes = ren.get_changes('SomeString')
   print(changes.description)
   print(changes.get_changed_resources()  # Files that would be changed.
   
3. Make the changes.
   project.do(changes)

What you should know
++++++++++++++++++++

You should understand Python's ast module.

Overview of type inference
++++++++++++++++++++++++++

- Startup process.
- Traversers.
- What is an inference?

How to run sphinx
+++++++++++++++++

To do: move this to a separate document.

Make sure conf.py can import rope.
- Add rope to the path (or sitecustomize.py) if necessary.
  
Add necessary modules:
- pip install sphinx_autodoc_typehints
- pip install tabulate
- pip install sphinx_rtd_theme

Run sphinx-build from the docs directory:
    
    docs>sphinx-build -M html . _build -a

