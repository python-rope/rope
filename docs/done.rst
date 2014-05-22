===========
 Done List
===========

> Public Release 0.10.0 : May 22, 2014

- Undre the new management! Matěj Cepl <mcepl@cepl.eu> takes hesitantly
  over

- Merged all available pull requests and patches to the main codebase

- Tests are green again


> Public Release 0.9.3 : February 4, 2010


- codeassist: proposals scopes and types revised : January 26, 2010


- codeassist: handling "builtin unknowns" : January 06, 2010


- refactor: fixed arguments in extracted method : December 26, 2009


- pycore: fixed project's property `source_folders` : October 26, 2009


- codeassist: better handling of unicode docstrings : August 20, 2009


- setup.py: don't include docs as package data : July 18, 2009


- fscommands: handle hg crew ui changes : May 04, 2009


- patchedast: handle ExtSlice node : April 29, 2009


> Public Release 0.9.2 : February 19, 2009


- caching all sub-modules in `autoimport` : February 18 : 2009


- extract method handles conditional variable updates : February 10, 2009


- added basic support for setuptools : January 15, 2009


- added `CompletionProposal.parameters` : November 4, 2008


- fix recursion when creating modules : October 31, 2008


> Public Release 0.9.1 : October 29, 2008


- added import_dynload_stdmods project variable : October 28, 2008


- finding dynload standard modules on windows : October 15, 2008


> Public Release 0.9 : October 3, 2008


- supporting Darcs VCS : August 20, 2008


- handling files with mac line-ending : July 25, 2008


- not searching all files when inlining a local variable : July 24, 2008


> Public Release 0.8.4 : June 24, 2008


- handling only_current for inline in other modules : July 21, 2008


- inlining variable in other modules : July 19, 2008


- added `rope.contrib.finderrors` : July 17, 2008


- added `rope.contrib.fixmodnames` : July 16, 2008


- added `rope.contrib.changestack` : July 15, 2008


- better extension module handling : June 29, 2008


- added `findit.Location.region` field : June 26, 2008


- added `rope.contrib.findit.find_definition()` : June 26, 2008


- added ``remove_self`` argument to `get_calltip()` : June 20, 2008


> Public Release 0.8.3 : June 20, 2008


- handling builtin modules in autoimport : June 12, 2008


- creating parent folders of ``.ropeproject`` if don't exist : June 6, 2008


- fixed inlining functions with line-breaks in arguments : May 22, 2008


- added lineno to `rope.contrib.findit.Location` : May 19, 2008


- deprecated some of `ChangeSignature` methods : May 19, 2008


- added `ChangeSignature.get_args()` : May 19, 2008


> Public Release 0.8.2 : May 10, 2008


- inlining parameters : May 10, 2008


- automatic default insertion in change signature : May 10, 2008


- adding underlined parameter to `AutoImport` : May 7, 2008


- added `rope.contrib.findit.find_implementations()` : April 28, 2008


- moved `find_occurrences()` to `rope.contrib.findit` : April 25, 2008


> Public Release 0.8.1 : April 20, 2008


- added GIT support in fscommands : April 19, 2008


- back importing underlined names in move : April 19, 2008


- added `codeassist.get_calltip()` : April 12, 2008


- added `libutils.analyze_modules()` : April 12, 2008


- added ``soa_followed_calls`` project config : April 11, 2008


- `libutils.report_change()` reads `automatic_soa` : April 10, 2008


- SOA can follow functions : April 10, 2008


- better handling of for, with and except variables : April 7, 2008


- not reparsing unchanged modules for code assists : April 6, 2008


- handling property as decorator : April 5, 2008


> Public Release 0.8 : April 5, 2008


- ignore_bad_imports project config : March 28, 2008


- added AutoImport.get_name_locations() : March 17, 2008


> Public Release 0.7.9 : March 14, 2008


- Deprecated codeassist templates : March 14, 2008


- Added in_hierarchy option to find occurrences : March 10, 2008


- Faster class hierarchy analysis for refactorings : March 10, 2008


- Added maxfixes to get doc and get definition location : March 6, 2008


- Added extension_modules project config : March 6, 2008


- Supporting builtin and c-extension modules : March 6, 2008


> Public Release 0.7.8 : March 1, 2008


- Extracting functions with only one return statement : February 29, 2008


- Reporting errors for exceptional conditions in usefunction : February 29, 2008


- More intelligent import handling for factory and move : February 25, 2008


- Handling future imports in organize imports : February 20, 2008


- Codeanalyze ignores comments when finding primaries : February 17, 2008


- Organize import and dynload builtin modules on unix : February 16, 2008


- Moved ImportOrganizer to rope.refactor.importutils : February 14, 2008


- Moved ModuleToPackage to rope.refactor.topackage : February 14, 2008


> Public Release 0.7.7 : February 13, 2008


- Added python_files project config : February 10, 2008


- Added codeassist.starting_expression() : February 10, 2008


- Added AutoImport.clear_cache() : February 7, 2008


- Improved extract function : February 1, 2008


- Handling except variables : January 29, 2008


> Public Release 0.7.6 : January 28, 2008


- Handling unsure matches in restructurings : January 27, 2008


- Added rope.contrib.autoimport : January 26, 2008


- Added use function refactoring : January 25, 2008


- Completing names after from-imports : January 23, 2008


- Adding resources parameter to some refactorings : January 22, 2008


- Deprecated in_file argument of `Rename.get_changes()` : January 22, 2008


> Public Release 0.7.5 : January 17, 2008


- Checking isinstance in restructurings : January 11, 2008


- Better handling of one-liners : January 10, 2008


- Choosing which files to apply a restructuring on : January 9, 2008


- Allowing customizable restructuring wildcards : January 7, 2008


> Public Release 0.7.4 : January 3, 2008


- Deprecated objectdb_type project config : December 23, 2007


- Added save_objectdb config : December 23, 2007


- Added compress_history and compress_objectdb configs : December 22, 2007


> Public Release 0.7.3 : December 19, 2007


- Inlining a single occurrence : December 13, 2007


- Global extract method/variable : December 13, 2007


> Public Release 0.7.2 : December 13, 2007


- Specifying the number of fixes in code_assist : December 10, 2007


- Deprecated `Pycore.create_(module|package)` : November 29, 2007


- Performing refactorings across multiple projects : November 29, 2007


> Public Release 0.7.1 : November 28, 2007


- Better handling of symlinks in project path : November 27, 2007


- Asking the user about unsure occurrences : November 10, 2007


> Public Release 0.7 : November 1, 2007


- ropemacs: moving elements, methods and modules : October 30, 2007


- ropemacs: undoing refactorings : October 29, 2007


- ropemacs: inline refactoring : October 29, 2007


- ropemacs: extract method and local variable : October 29, 2007


- ropemacs: goto definition : October 29, 2007


- ropemacs: rename refactoring : October 29, 2007


- A new open project dialog : October 10, 2007


- Added `Core.add_extension()` : September 19, 2007


> Public Release 0.6.2 : September 9, 2007


- Setting statusbar, menu and bufferlist fonts in ``~/.rope`` : September 8, 2007


- Better kill line : September 8, 2007


- Using ``/``\s to match parent folders in find file : September 5, 2007


- Fixed matching method implicit argument when extracting : September 5, 2007


- An option for not removing the definition after inlining : September 1, 2007


- Performing import actions on individual imports : September 1, 2007


- ``C-u`` action prefix : September 1, 2007


- Changing inline and move to use froms for back imports : August 27, 2007


> Public Release 0.6.1 : August 19, 2007


- Cleaning up `rope.ide.codeassist` : August 19, 2007


- Showing unsure occurrences in show occurrences : August 17, 2007


- Sorting scopes : August 9, 2007


> Public Release 0.6 : August 5, 2007


- Finding the scope in an overwritten scope : August 4, 2007


- Added ``ignore_syntax_errors`` project config : August 2, 2007


> Public Release 0.6m6 : July 29, 2007


- Better diff highlighting : July 20, 2007


- Handling imports when inlining : July 20, 2007


- Handling recursive restructurings : July 18, 2007


> Public Release 0.6m5 : July 15, 2007


- Next/prev scope; ``M-C-e/M-C-a`` : July 9, 2007


- Next/prev statement; ``M-e/M-a`` : July 8, 2007


- Importing modules in restructurings : July 7, 2007


- Auto-indentation in restructurings : July 6, 2007


> Public Release 0.6m4 : July 1, 2007


- Adding tools for making using rope library easier : June 23, 2007


- Separating rope library from rope IDE : June 20, 2007


- Restructuring checks for builtin objects using `__builtin__` : June 20, 2007


> Public Release 0.6m3 : June 17, 2007


- Self assignment warning : June 17, 2007


- Adding support for Mercurial VCS : June 17, 2007


- Inferring the object, list comprehensions hold : June 6, 2007


> Public Release 0.6m2 : June 3, 2007


- Enhancing extract method on staticmethods/classmethods : June 2, 2007


- Extracting similar expressions/statements : May 30, 2007


- Adding checks in restructuring dialog : May 23, 2007


- Using `_ast` instead of `compiler` : May 23, 2007


> Public Release 0.6m1 : May 20, 2007


- Adding custom source folders in ``config.py`` : May 15, 2007


- A simple UI for performing restructurings : May 15, 2007


- Restructurings : May 14, 2007


- Finding similar code : May 13, 2007


- Patching ASTs to include formatting information : May 9, 2007


> Public Release 0.5 : May 6, 2007


- Better dialogs : May 2, 2007


> Public Release 0.5rc1 : April 29, 2007


- Showing current file history; ``C-x p 1 h`` : April 28, 2007


- Open Type; ``C-x C-t`` : April 23, 2007


- Adding persisted_memory objectdb : April 20, 2007


- Adding sqlite objectdb : April 20, 2007


> Public Release 0.5m5 : April 15, 2007


- Encapsulating field in the defining class : April 13, 2007


- Renaming occurrences in strings and comments : April 13, 2007


- Stoppable refactorings : April 11, 2007


- Faster automatic SOI analysis : April 9, 2007


- Basic implicit interfaces : April 9, 2007


- Automatic SOI analysis : April 6, 2007


- Using a better object textual form : April 4, 2007


- Spell-Checker : April 3, 2007


> Public Release 0.5m4 : April 1, 2007


- Incremental ObjectDB validation : March 31, 2007


- Saving history across sessions : March 29, 2007


- Saving object data to disk : March 28, 2007


- Adding `.ropeproject` folder : Mark 26, 2007


- Inlining `staticmethod`\s : March 23, 2007


- Saving locations and texts : March 23, 2007


- Generating python elements : March 21, 2007


> Public Release 0.5m3 : March 18, 2007


- Holding per name information for builtin containers : March 17, 2007


- Filling paragraphs in text modes; ``M-q`` : March 15, 2007


- Yanking; ``M-y`` : March 13, 2007


- Repeating last command; ``C-x z`` : March 13, 2007


- Adding 'rename when unsure' option : March 13, 2007


- Change signature for constructors : March 11, 2007


- Supporting generator functions : March 9, 2007


- Enhancing show pydoc to include docs from superclasses : March 8, 2007


- Enhanced returned object static object inference : March 8, 2007


- Enhanced static object inference : March 8, 2007


- Handling ``*args`` and ``**kwds`` arguments : March 7, 2007


- Showing pydoc for some of builtin types and functions : March 7, 2007


> Public Release 0.5m2 : March 4, 2007


- Showing codetag/error/warning list : March 3, 2007


- Registering templates in ``~/.rope`` : February 26, 2007


- Auto-completing function keyword arguments when calling : February 26, 2007


- Better status bar : February 23, 2007


- Change occurrences : February 23, 2007


- Moving methods : February 21, 2007


> Public Release 0.5m1 : February 18, 2007


- Handling ``with`` statements : February 15, 2007


- Performing change signature in class hierarchies : February 14, 2007


- Supporting builtin `zip` and `enumerate` : February 14, 2007


- Replace method with method object : February 12, 2007


- Enhancing searching : February 10, 2007


- Execute command; ``M-x`` : February 10, 2007


- Changing editor font and keybinding in ``~/.rope`` : February 9, 2007


- Having two keybindings emacs/normal : February 9, 2007


- Handling multi-key keyboard shortcuts : February 8, 2007


- Fixing removing imports that eat the blank lines : February 8, 2007


- Removing extra spaces and lines; ``C-c C-f`` : February 7, 2007


> Public Release 0.4 : February 4, 2007


- Reporting some of the refactoring problems in the UI : February 1, 2007


> Public Release 0.4rc1 : January 28, 2007


- Project History; Undoing refactorings in any order : January 25, 2007


- Handling ``global`` keywords : January 22, 2007


- Undoing everything; Project history : January 21, 2007


- Removing `PythonRefactoring` facade : January 19, 2007


- Basic lambdas handling : January 16, 2007


- Handling builtin `property` : January 14, 2007


> Public Release 0.4m5 : January 14, 2007


- Handling long imports : January 11, 2007


- Builtin functions : super, sorted, reversed, range : January 7, 2007


- Support for file/open builtin type : January 7, 2007


- Sorting imports; standard, third party, project : January 7, 2007


- Enhanced dynamic object inference : January 5, 2007


> Public Release 0.4m4 : December 31, 2006


- Basic support for builtin types : December 29, 2006


- Find occurrences; ``C-G`` : December 26, 2006


- Ignoring ``*.pyc``, ``*~`` and ``.svn`` : December 26, 2006


- Moving/renaming current module/package : December 25, 2006


- Removing imports from the same module : December 22, 2006


- Goto last edit location; ``C-q`` : December 20, 2006


- Trying ``utf-8`` if defaults don't work : December 19, 2006


- Comment line and region; ``C-c c``, ``C-c C-c`` : December 18, 2006


> Public Release 0.4m3 : December 17, 2006


- Introduce parameter : December 14, 2006


- 8 spaces per tabs in `rope.base` and `rope.refactor` : December 8, 2006


- Better support for other version control systems : December 8, 2006


- Updating files that have been changed : December 8, 2006


- Fixing module running on Windows : December 6, 2006


> Public Release 0.4m2 : December 3, 2006


- Change method signature : December 1, 2006


- Change method signature dialog : November 30, 2006


- Reordering parameters : November 28, 2006


- Removing parameters : November 26, 2006


- Inline parameter default value : November 26, 2006


- Adding parameters : November 26, 2006


- Normalizing function calls : November 26, 2006


> Public Release 0.4m1 : November 19, 2006


- Better help menu : November 15, 2006


- Inline method refactoring : November 10, 2006


> Public Release 0.3 : November 5, 2006


- Better code assist proposal sorting and dialog : November 3, 2006


- Extract method works with normal selection : October 31, 2006


- Basic python file encoding support : October 31, 2006


> Public Release 0.3rc1 : October 29, 2006


- Unit-test running view : October 28, 2006


- Previewing refactoring changes : October 25, 2006


- Encapsulate field : October 19, 2006


- Convert local variable to field refactoring : October 18, 2006


> Public Release 0.3m5 : October 15, 2006


- Code completions inside uncompleted ``try`` blocks : October 7, 2006


- Single line extract method and variable : October 7, 2006


- Hiding unappropriate menu items in different contexts : October 6, 2006


- Inline local variable : October 5, 2006


- Rename function parameters : October 5, 2006


- Move a module or package to another package : October 4, 2006


> Public Release 0.3m4 : October 1, 2006


- Showing function signature in show doc : September 29, 2006


- Goto line : September 29, 2006


- Move refactoring for global class/function : September 29, 2006


- Change relative imports to absolute : September 28, 2006


- Changing from imports to normal imports : September 28, 2006


- Removing duplicate imports : September 27, 2006


- Expanding from-star-imports : September 27, 2006


- Removing unused imports : September 27, 2006


- Introduce factory method refactoring : September 25, 2006


- Basic import tools : September 21, 2006


- Separating concluded and structural data in `PyModule`\s : September 19, 2006


> Public Release 0.3m3 : September 17, 2006


- Basic subversion support using pysvn : September 14, 2006


- Renaming methods in class hierarchy : September 12, 2006


- Transform module to package refactoring : September 11, 2006


> Public Release 0.3m2 : September 3, 2006


- Better New ... Dialogs : September 2, 2006


- Function argument dynamic object inference : September 2, 2006


- Basic dynamic type inference : September 2, 2006


- Better menus : August 27, 2006


- Relative imports : August 23, 2006


- Read ``__init__.py`` of packages : August 23, 2006


- Extract function : August 22, 2006


> Public Release 0.3m1 : August 20, 2006


- Undoing refactorings : August 19, 2006


- Making module dependancy graph : August 19, 2006


- Rename modules/packages : August 18, 2006


- Reloading changed editors after refactorings : August 17, 2006


- Rename class/function : August 17, 2006


- Function return object static type inference : August 15, 2006


- Show PyDoc : August 15, 2006


- Object inference for chained assignments : August 14, 2006


> Public Release 0.2 : August 6, 2006


- Resource tree view : August 5, 2006


- Handle ``HTTPClient`` style names in go to next/prev word : August 2, 2006


> Public Release 0.2RC : July 30, 2006


- Asking whether to save modified buffers when exiting : July 29, 2006


- Extending menus : July 25, 2006


- ReST highlighting : July 24, 2006


- Showing editor modified status : July 23, 2006


- Sorting code assist proposals : July 22, 2006


- Not renaming names in strings and comments in refactorings : July 22, 2006


- Separating entering and correcting indentation : July 22, 2006


> Public Release 0.2pre5 : July 16, 2006


- Out of project modules : July 15, 2006


- Handle circular from-imports : July 14, 2006


- Completeing ``AClass(param).a_`` : July 11, 2006


- We know the type of ``var = AClass()`` : July 4, 2006


- Rename function parameter in the function : July 3, 2006


> Public Release 0.2pre4 : July 2, 2006


- Rename local variable : July 2, 2006


- Complete as you type : July 2, 2006


- Show quick outline; C-o : June 23, 2006


- Go to definition; F3 : June 22, 2006


> Public release 0.2pre3 : June 18, 2006


- Auto-completing "self."s : June 13, 2006


- Proposing base class attributes : June 12, 2006


- Auto completion after "."s : June 8, 2006


> Public Release 0.2pre2 : June 4, 2006


- Next/prev word stops at underlines and capitals : May 29, 2006


- Ignoring string and comment contents while indenting : May 29, 2006


- Proposing templates in code-assist proposals : May 26, 2006


- Auto-complete from-import imported objects : May 25, 2006


- Not proposing variables which are not defined yet : May 23, 2006


- Auto-completion should ignore current statement : May 23, 2006


- Proposing function parameters in functions : May 22, 2006


- Auto-complete local variable names : May 22, 2006


> Public Release 0.2pre1 : May 20, 2006


- Auto completing keywords and builtins : May 19, 2006


- Auto-complete imported objects : May 19, 2006


- Show searching status in the status bar : May 18, 2006


- Auto-complete class and function names : May 16, 2006


- Auto-complete global variables : May 14, 2006


> Public Release 0.1 : May 8, 2006


- Separating indenting and correcting indentation : May 7, 2006


- Enhancing editor and indentation : May 4, 2006

  - Pressing backspace should deindent
  - Clearing undo list when opening a file; undoSeparator when saving


- Showing current line in status bar : April 28, 2006


- Switch editor dialog; C-x b and C-F6 : April 27, 2006


- Make new package dialog : April 25, 2006


- Make new module dialog : April 25, 2006


> Public Release 0.1pre : April 22, 2006


- Extending syntax highlighted elements : April 22, 2006


- Auto indentation; C-i : April 20, 2006


- Basic searching; C-s : April 12, 2006


> SF registration : April 10, 2006


- Multiple buffers : April 8, 2006
  The editor should have a notebook view.


- Enhancing dialogs : April 7, 2006
  Using tkMessageBox, tkFileDialog, tkSimpleDialog, ScrolledText


- Running modules : April 6, 2006
  You should add the required directories to the python path.


- Guessing source folders in the project : April 5, 2006


- Finding a file in a project : April 4, 2006


- Highlighting keywords : March 21, 2006
  Only python files(``*.py``) should be highlighted.
