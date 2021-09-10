---
name: Bug report
about: Unexpected result when doing a refactoring operation
title: ''
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Code before refactoring:

```
foo = bar + 1
```

2. Describe the refactoring you want to do

3. Expected code after refactoring:

```
def extracted(bar)
    return bar + 1
foo = extracted(bar)
```

4. Describe the error or unexpected result that you are getting

```
def extracted(bar)
    return bar + 9000
foo = extracted(bar)
```

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Editor information (please complete the following information):**
 - Project Python version: ...
 - Rope Python version: ...
 - Rope version: ...
 - Text editor/IDE and version: ...

**Additional context**
Add any other context about the problem here.
