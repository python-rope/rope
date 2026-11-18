"""Verify built markers and the installed wheel's closed filesystem contract."""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import venv
import zipfile
from importlib.metadata import version
from pathlib import Path

import toml


def installed_contract(expected_version, contract):
    import rope

    origin = Path(rope.__file__).resolve()
    installed = Path(sysconfig.get_path("purelib")).resolve()
    if not origin.is_relative_to(installed):
        raise RuntimeError(f"rope did not load from the installed wheel: {origin}")
    if version("rope") != expected_version:
        raise RuntimeError("installed rope version differs from the built artifact")
    print(f"Installed rope {version('rope')} from {origin}", flush=True)
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-m",
            "pytest",
            "-v",
            "-ra",
            "-c",
            str(contract.parent / "pyproject.toml"),
            "--rootdir",
            str(contract.parent),
            "--confcutdir",
            str(contract.parent),
            str(contract),
        ],
        cwd=contract.parent,
        check=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed-contract", action="store_true")
    parser.add_argument("--expected-version")
    parser.add_argument("--contract", type=Path)
    arguments = parser.parse_args()
    if arguments.installed_contract:
        if arguments.expected_version is None or arguments.contract is None:
            parser.error("installed contract requires its version and contract path")
        installed_contract(arguments.expected_version, arguments.contract)
        return
    source_root = Path(__file__).resolve().parents[1]
    release = toml.load(source_root / "pyproject.toml")["project"]["version"]
    wheel = Path("dist") / f"rope-{release}-py3-none-any.whl"
    sdist = Path("dist") / f"rope-{release}.tar.gz"
    for artifact in (wheel, sdist):
        print(f"SHA256 {artifact} {hashlib.sha256(artifact.read_bytes()).hexdigest()}", flush=True)
    with zipfile.ZipFile(wheel) as artifact:
        assert artifact.read("rope/py.typed") == b""
    with tarfile.open(sdist) as artifact:
        marker = artifact.extractfile(f"rope-{release}/rope/py.typed")
        assert marker is not None
        with marker:
            assert marker.read() == b""
    print(f"Verified rope/py.typed in {wheel} and {sdist}")
    environment = Path(sys.prefix).resolve()
    if environment == Path(sys.base_prefix).resolve() or environment.is_relative_to(source_root):
        raise RuntimeError("artifact validation requires an exclusive environment outside the checkout")
    with tempfile.TemporaryDirectory(
        prefix="rope-artifact-runtime-", dir=environment.parent
    ) as directory:
        runtime = Path(directory)
        target = runtime / "venv"
        venv.EnvBuilder(with_pip=True).create(target)
        python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        consumer_environment = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith("PYTEST_")
        }
        consumer_environment["PIP_CACHE_DIR"] = str(runtime / "pip-cache")
        subprocess.run(
            [str(python), "-I", "-m", "pip", "install", f"{wheel.resolve()}[dev]"],
            cwd=runtime,
            env=consumer_environment,
            check=True,
        )
        contract = runtime / "snapshot_resource_contracttest.py"
        shutil.copyfile(source_root / "ropetest" / contract.name, contract)
        shutil.copyfile(source_root / "pyproject.toml", runtime / "pyproject.toml")
        subprocess.run(
            [
                str(python), "-I", str(Path(__file__).resolve()),
                "--installed-contract", "--expected-version", release,
                "--contract", str(contract),
            ],
            cwd=runtime,
            env=consumer_environment,
            check=True,
        )


if __name__ == "__main__":
    main()
