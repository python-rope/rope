import hashlib

import rope


def calculate_version_hash():
    hasher = hashlib.sha1(f"{rope.VERSION}".encode("ascii"))
    return hasher.hexdigest()
