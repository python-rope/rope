from pathlib import Path
from typing import Callable, Dict, List, Optional

from pydantic import BaseModel, Field
from pytoolconfig import PyToolConfig, generate_documentation
from pytoolconfig.sources import Source

from rope.base.resources import Folder
from rope.base.utils import pycompat


class RopePrefs(BaseModel):
    ignored_resources: List[str] = Field(
        default=[
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
        ],
        description="""    
Specify which files and folders to ignore in the project.
Changes to ignored resources are not added to the history and
VCSs.  Also they are not returned in `Project.get_files()`.
Note that ``?`` and ``*`` match all characters but slashes. 
'*.pyc': matches 'test.pyc' and 'pkg/test.pyc'
'mod*.pyc': matches 'test/mod1.pyc' but not 'mod/1.pyc'
'.svn': matches 'pkg/.svn' and all of its children
'build/*.o': matches 'build/lib.o' but not 'build/sub/lib.o'
'build//*.o': matches 'build/lib.o' and 'build/sub/lib.o'
""",
    )
    save_objectdb: bool = Field(
        default=False, description="Should rope save object information or not."
    )
    compress_objectdb: bool = False
    automatic_soa: bool = True
    soa_followed_calls: int = Field(
        default=0, description="The depth of calls to follow in static object analysis"
    )
    preform_doa: bool = Field(
        default=True,
        description="""
If `False` when running modules or unit tests 'dynamic object analysis' is turned off. This makes them much faster.
""",
    )
    validate_objectdb: bool = Field(
        default=False,
        description="Rope can check the validity of its object DB when running.",
    )

    max_history_items: int = Field(default=32, description="How many undos to hold?")
    save_history: bool = Field(
        default=True, description="Shows whether to save history across sessions."
    )
    compress_history: bool = False

    indent_size: int = Field(
        default=4,
        description="""
Set the number spaces used for indenting.  According to
:PEP:`8`, it is best to use 4 spaces.  Since most of rope's
unit-tests use 4 spaces it is more reliable, too.
""",
    )

    extension_modules: List[str] = Field(
        default=[],
        description="Builtin and c-extension modules that are allowed to be imported and inspected by rope.",
    )

    import_dynload_stdmods: bool = Field(
        default=True,
        description="Add all standard c-extensions to extension_modules list.",
    )
    ignore_syntax_errors = Field(default=False)

    ignore_bad_imports = Field(
        default=False,
        description="If `True`, rope ignores unresolvable imports.  Otherwise, they appear in the importing namespace.",
    )

    # If `True`, rope will insert new module imports as
    # `from <package> import <module>` by default.
    prefer_module_from_imports = Field(default=False)

    # If `True`, rope will transform a comma list of imports into
    # multiple separate import statements when organizing
    # imports.
    split_imports = Field(default=False)

    # If `True`, rope will remove all top-level import statements and
    # reinsert them at the top of the module when making changes.
    pull_imports_to_top = Field(default=True)

    sort_imports_alphabetically = Field(
        default=False,
        description="""
If `True`, rope will sort imports alphabetically by module name instead
of alphabetically by import statement, with from imports after normal
imports.
""",
    )
    type_hinting_factory: str = Field(
        "rope.base.oi.type_hinting.factory.default_type_hinting_factory",
        description="""
Location of implementation of
rope.base.oi.type_hinting.interfaces.ITypeHintingFactory In general
case, you don't have to change this value, unless you're an rope expert.
Change this value to inject you own implementations of interfaces
listed in module rope.base.oi.type_hinting.providers.interfaces
For example, you can add you own providers for Django Models, or disable
the search type-hinting in a class hierarchy, etc.
""",
    )
    project_opened: Optional[Callable] = Field(
        None, description="""This function is called after opening the project"""
    )


class _RopeConfigSource(Source):
    """Custom source for rope config.py files."""

    name: str = "config.py"
    run_globals: Dict

    def __init__(self, ropefolder: Folder):
        self.ropefolder = ropefolder
        self.prefs = {}
        self.run_globals = {}

    def _read(self) -> bool:
        if self.ropefolder is None or not self.ropefolder.has_child("config.py"):
            return False
        config = self.ropefolder.get_child("config.py")
        self.run_globals.update(
            {
                "__name__": "__main__",
                "__builtins__": __builtins__,
                "__file__": config.real_path,
            }
        )
        pycompat.execfile(config.real_path, self.run_globals)
        return True

    def parse(self) -> Optional[Dict]:
        if not self._read():
            return None
        if "set_prefs" in self.run_globals:
            self.run_globals["set_prefs"](self.prefs)
        if "project_opened" in self.run_globals:
            self.prefs["project_opened"] = self.run_globals["project_opened"]
        return self.prefs


def get_config(root: Folder, ropefolder: Folder) -> PyToolConfig:
    custom_sources = [_RopeConfigSource(ropefolder)]
    config = PyToolConfig(
        "rope",
        root.pathlib,
        RopePrefs,
        custom_sources=custom_sources,
        bases=[".ropefolder"],
        recursive=False,
    )
    return config


def _gen_config_doc():
    from rope.base.project import Project  # prevent circular import

    root = Path(__file__).parent.parent.parent
    config = get_config(Project(str(root)).root, None)
    generate_documentation(config, root / "CONFIGURATION.md")
