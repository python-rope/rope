import os
import os.path

def remove_recursively(file):
    if not os.path.exists(file):
        return
    for root, dirs, files in os.walk(file, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(file)

