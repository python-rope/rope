import hashlib
import json

import rope
import rope.base.project


def calculate_version_hash(project: rope.base.project.Project) -> str:
    hasher = hashlib.sha1()

    version_data = f"{rope.VERSION}"
    hasher.update(version_data.encode("ascii"))

    serialized_prefs_data = _prefs_version_hash_data(project)
    hasher.update(serialized_prefs_data.encode("ascii"))

    return hasher.hexdigest()


def _prefs_version_hash_data(project):
    prefs_data = dict(vars(project.prefs))
    del prefs_data["callbacks"]
    return json.dumps(prefs_data, sort_keys=True, indent=2)
