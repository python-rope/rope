Configuration
=============
Rope supports the following configuration formats

1. pyproject.toml
2. config.py 

pyproject.toml 
--------------
Will be used if [tool.rope] is configured.

.. code-block:: toml 
   
    [tool.rope]
    compress_objectdb = true

config.py 
---------
You can also configure rope via a config.py in the ropefolder directory.   
It will be used if ``[tool.rope]`` is not present in ``pyproject.toml`` or ``pyproject.toml`` isn't present and config.py is present.

.. code-block:: python3
    
    def set_prefs(prefs):
        prefs["ignored_resources"] = [
            "*.pyc",
            "*~",
            ".ropeproject",
            ".hg",
            ".svn",
            "_svn",
            ".git",
            ".tox",
            ".venv",
            "venv",
        ]

Additionally, you can run an executable function at startup of rope. 

.. code-block:: python3 
   
    def project_opened(project):
        """This function is called after opening the project"""
        # Do whatever you like here!




Options
-------
.. autopytoolconfigtable:: rope.base.prefs.Prefs

Old Configuration File
----------------------
This is a sample config.py. While this config.py works and all options here should be supported, the above documentation reflects the latest version of rope.

.. literalinclude:: default_config.py  
   :language: python3
