class AClass(object):
    pass
def a_func(arg):
    return eval("arg()")
a_var = a_func(AClass)
print(a_var)
