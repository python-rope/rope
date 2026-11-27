"""Project file system commands.

This modules implements file system operations used by rope.  Different
version control systems can be supported by implementing the interface
provided by `FileSystemCommands` class.  See `SubversionCommands` and
`MercurialCommands` for example.

"""

import codecs
import os
import shutil
import subprocess
import tokenize
import typing

FileContent = typing.NewType("FileContent", bytes)


def create_fscommands(root):
    dirlist = os.listdir(root)
    commands = {
        ".hg": MercurialCommands,
        ".svn": SubversionCommands,
        ".git": GITCommands,
        "_svn": SubversionCommands,
        "_darcs": DarcsCommands,
    }
    for key in commands:
        if key in dirlist:
            try:
                return commands[key](root)
            except (ImportError, OSError):
                pass
    return FileSystemCommands()


class FileSystemCommands:
    def create_file(self, path):
        open(path, "w").close()

    def create_folder(self, path):
        os.mkdir(path)

    def move(self, path, new_location):
        shutil.move(path, new_location)

    def remove(self, path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)

    def write(self, path, data):
        file_ = open(path, "wb")
        try:
            file_.write(data)
        finally:
            file_.close()

    def read(self, path):
        with open(path, "rb") as handle:
            return handle.read()


class SubversionCommands:
    def __init__(self, *args):
        self.normal_actions = FileSystemCommands()
        import pysvn  # type: ignore

        self.client = pysvn.Client()

    def create_file(self, path):
        self.normal_actions.create_file(path)
        self.client.add(path, force=True)

    def create_folder(self, path):
        self.normal_actions.create_folder(path)
        self.client.add(path, force=True)

    def move(self, path, new_location):
        self.client.move(path, new_location, force=True)

    def remove(self, path):
        self.client.remove(path, force=True)

    def write(self, path, data):
        self.normal_actions.write(path, data)

    def read(self, path):
        return self.normal_actions.read(path)


class MercurialCommands:
    def __init__(self, root):
        self.hg = self._import_mercurial()
        self.normal_actions = FileSystemCommands()
        try:
            self.ui = self.hg.ui.ui(
                verbose=False,
                debug=False,
                quiet=True,
                interactive=False,
                traceback=False,
                report_untrusted=False,
            )
        except Exception:
            self.ui = self.hg.ui.ui()
            self.ui.setconfig("ui", "interactive", "no")
            self.ui.setconfig("ui", "debug", "no")
            self.ui.setconfig("ui", "traceback", "no")
            self.ui.setconfig("ui", "verbose", "no")
            self.ui.setconfig("ui", "report_untrusted", "no")
            self.ui.setconfig("ui", "quiet", "yes")

        self.repo = self.hg.hg.repository(self.ui, root)

    def _import_mercurial(self):
        import mercurial.commands  # type: ignore
        import mercurial.hg  # type: ignore
        import mercurial.ui  # type: ignore

        return mercurial

    def create_file(self, path):
        self.normal_actions.create_file(path)
        self.hg.commands.add(self.ui, self.repo, path)

    def create_folder(self, path):
        self.normal_actions.create_folder(path)

    def move(self, path, new_location):
        self.hg.commands.rename(self.ui, self.repo, path, new_location, after=False)

    def remove(self, path):
        self.hg.commands.remove(self.ui, self.repo, path)

    def write(self, path, data):
        self.normal_actions.write(path, data)

    def read(self, path):
        return self.normal_actions.read(path)


class GITCommands:
    def __init__(self, root):
        self.root = root
        self._do(["version"])
        self.normal_actions = FileSystemCommands()

    def create_file(self, path):
        self.normal_actions.create_file(path)
        self._do(["add", self._in_dir(path)])

    def create_folder(self, path):
        self.normal_actions.create_folder(path)

    def move(self, path, new_location):
        self._do(["mv", self._in_dir(path), self._in_dir(new_location)])

    def remove(self, path):
        self._do(["rm", self._in_dir(path)])

    def write(self, path, data):
        # XXX: should we use ``git add``?
        self.normal_actions.write(path, data)

    def read(self, path):
        return self.normal_actions.read(path)

    def _do(self, args):
        _execute(["git"] + args, cwd=self.root)

    def _in_dir(self, path):
        if path.startswith(self.root):
            return path[len(self.root) + 1 :]
        return self.root


class DarcsCommands:
    def __init__(self, root):
        self.root = root
        self.normal_actions = FileSystemCommands()

    def create_file(self, path):
        self.normal_actions.create_file(path)
        self._do(["add", path])

    def create_folder(self, path):
        self.normal_actions.create_folder(path)
        self._do(["add", path])

    def move(self, path, new_location):
        self._do(["mv", path, new_location])

    def remove(self, path):
        self.normal_actions.remove(path)

    def read(self, path):
        return self.normal_actions.read(path)

    def write(self, path, data):
        self.normal_actions.write(path, data)

    def _do(self, args):
        _execute(["darcs"] + args, cwd=self.root)


def _execute(args, cwd=None):
    process = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE)
    process.wait()
    return process.returncode


def unicode_to_file_data(contents: str, encoding=None, newlines=None) -> FileContent:
    assert isinstance(contents, str)
    if newlines and newlines != "\n":
        contents = contents.replace("\n", newlines)
    if encoding is None:
        encoding = read_str_coding(contents)
        # Avoid prepending a duplicate UTF-8 BOM when `utf-8-sig` was inferred
        # from a leading U+FEFF already present in `contents`.
        if (
            encoding is not None
            and contents.startswith("\ufeff")
            and _is_utf8_sig(encoding)
        ):
            encoding = "utf-8"
    if encoding is not None:
        return FileContent(contents.encode(encoding))
    return FileContent(contents.encode("utf-8"))


def file_data_to_unicode(data, encoding=None):
    result, _ = _decode_data_with_encoding(data, encoding)
    newline = "\n"
    if "\r\n" in result:
        result = result.replace("\r\n", "\n")
        newline = "\r\n"
    if "\r" in result:
        result = result.replace("\r", "\n")
        newline = "\r"
    return result, newline


def _decode_data(data, encoding):
    result, _ = _decode_data_with_encoding(data, encoding)
    return result


def _decode_data_with_encoding(data, encoding):
    if isinstance(data, str):
        return data, encoding
    if encoding is None:
        encoding = read_str_coding(data)
    if encoding is None:
        # Fallback when tokenize.detect_encoding() could not determine a valid encoding.
        encoding = "utf-8"
    try:
        return data.decode(encoding), encoding
    except (UnicodeError, LookupError):
        # fallback to latin1: it should never fail
        return data.decode("latin1"), "latin1"


def _is_utf8_sig(encoding: str) -> bool:
    try:
        return codecs.lookup(encoding).name == "utf-8-sig"
    except LookupError:
        return False


def _iter_first_two_lines(
    source: typing.Union[str, bytes],
) -> typing.Iterator[bytes]:
    """Lazily yield up to the first two lines of `source` as bytes.

    Splits only on CRLF, LF, or CR (matching PEP 263 / bytes line-ending rules)
    so control characters such as form-feed (`\\f`) on line 1 are preserved,
    and avoids scanning beyond the first two lines on large files.

    For `str` inputs, non-ASCII characters (other than a leading U+FEFF BOM)
    are replaced with `?` so `tokenize.detect_encoding()` can detect a PEP 263
    coding cookie without failing when validating UTF-8 bytes against a
    non-UTF-8 declared encoding (e.g. cp1252 on Python 3.14.1+).
    """
    is_str = isinstance(source, str)
    lf = "\n" if is_str else b"\n"
    cr = "\r" if is_str else b"\r"
    pos = 0
    length = len(source)
    for line_index in range(2):
        if pos >= length:
            break
        nl_idx = source.find(lf, pos)
        cr_idx = source.find(cr, pos, nl_idx) if nl_idx != -1 else source.find(cr, pos)
        if cr_idx != -1:
            end = cr_idx + 2 if nl_idx == cr_idx + 1 else cr_idx + 1
        elif nl_idx != -1:
            end = nl_idx + 1
        else:
            end = length
        chunk = source[pos:end]
        pos = end
        if is_str:
            assert isinstance(chunk, str)
            if line_index == 0 and chunk.startswith("\ufeff"):
                yield codecs.BOM_UTF8 + chunk[1:].encode("ascii", errors="replace")
            else:
                yield chunk.encode("ascii", errors="replace")
        else:
            assert isinstance(chunk, bytes)
            yield chunk


def _sanitize_non_ascii_bytes(line: bytes) -> bytes:
    return bytes(byte if byte < 0x80 else ord("?") for byte in line)


def read_str_coding(source: typing.Union[str, bytes]) -> typing.Optional[str]:
    """Detect source encoding via PEP 263 / `tokenize.detect_encoding()`.

    Returns `None` if `tokenize.detect_encoding()` cannot determine a valid
    encoding (e.g. invalid UTF-8 in the first two lines without a coding
    cookie, an unknown/non-text encoding name, or a UTF-8 BOM that conflicts
    with the declared coding cookie).
    """
    line_iter = _iter_first_two_lines(source)
    consumed: typing.List[bytes] = []

    def readline() -> bytes:
        line = next(line_iter, b"")
        if line:
            consumed.append(line)
        return line

    try:
        encoding, _ = tokenize.detect_encoding(readline)
        # Reject non-text or unusable codecs (e.g. rot_13, undefined)
        # consistently across Python versions.
        "a".encode(encoding)
    except (LookupError, UnicodeError):
        return None
    except SyntaxError:
        # On Python < 3.14.1, tokenize.detect_encoding() decodes the cookie line
        # as UTF-8 before matching the PEP 263 cookie, causing valid non-UTF-8
        # files with non-ASCII bytes on the coding line itself (e.g. cp1252) to
        # raise SyntaxError. Retry with non-ASCII bytes sanitized to ASCII and
        # validate the consumed raw lines against the declared encoding (matching
        # CPython 3.14.1+ behavior), unless a UTF-8 BOM is present.
        if not isinstance(source, bytes) or source.startswith(codecs.BOM_UTF8):
            return None
        for extra in line_iter:
            consumed.append(extra)
        sanitized_iter = iter(_sanitize_non_ascii_bytes(line) for line in consumed)
        try:
            encoding, detected_lines = tokenize.detect_encoding(
                lambda: next(sanitized_iter, b"")
            )
        except (SyntaxError, LookupError):
            return None
        try:
            if codecs.lookup(encoding).name == "utf-8":
                return None
            "a".encode(encoding)
            for line in consumed[: len(detected_lines)]:
                line.decode(encoding)
        except (UnicodeError, LookupError):
            return None
        return encoding
    return encoding
