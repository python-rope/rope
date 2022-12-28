import hashlib
import importlib.util
import json

import rope.base.project


def calculate_version_hash(project: rope.base.project.Project) -> str:
    hasher = hashlib.sha256()

    version_data = f"{rope.VERSION}"
    hasher.update(version_data.encode("ascii"))

    hashed_prefs_data = _prefs_version_hash_data(project)
    hasher.update(hashed_prefs_data.encode("ascii"))

    schema_file_hash = _schema_file_hash("rope.contrib.autoimport.models")
    hasher.update(schema_file_hash.encode("ascii"))
    return hasher.hexdigest()


def _prefs_version_hash_data(project):
    prefs_data = dict(vars(project.prefs))
    del prefs_data["project_opened"]
    del prefs_data["callbacks"]
    del prefs_data["dependencies"]
    serialized_prefs_data = json.dumps(prefs_data, sort_keys=True, indent=2)
    return hashlib.sha256(serialized_prefs_data.encode("utf-8")).hexdigest()


def _schema_file_hash(module_name):
    models_module = importlib.util.find_spec(module_name)
    src = models_module.loader.get_source(module_name)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()
