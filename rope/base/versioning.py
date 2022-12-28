import hashlib

import rope
import rope.base.project


def calculate_version_hash(project: rope.base.project.Project) -> str:
    hasher = hashlib.sha1(f"{rope.VERSION}".encode("ascii"))
    return hasher.hexdigest()
