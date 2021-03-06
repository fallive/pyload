#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals

import inspect
import io
import os
import re
from contextlib import nested

from future import standard_library

from pyload.core import info
from thrift.Thrift import TType
from thriftgen.pyload import Pyload, ttypes

standard_library.install_aliases()


path = os.path.abspath(os.path.dirname(__file__))
root = os.path.abspath(os.path.join(path, "..", ".."))


type_map = {
    TType.BOOL: 'bool',
    TType.DOUBLE: 'float',
    TType.I16: 'int',
    TType.I32: 'int',
    TType.I64: 'int',
    TType.STRING: 'str',
    TType.MAP: 'dict',
    TType.LIST: 'list',
    TType.SET: 'set',
    TType.VOID: 'None',
    TType.STRUCT: 'BaseObject',
    TType.UTF8: 'str',
}


def get_spec(spec, optional=False):
    """
    Analyze the generated spec file and writes information into file.
    """
    if spec[1] == TType.STRUCT:
        return spec[3][0].__name__
    elif spec[1] == TType.LIST:
        if spec[3][0] == TType.STRUCT:
            ttype = spec[3][1][0].__name__
        else:
            ttype = type_map[spec[3][0]]
        return "(list, {0})".format(ttype)
    elif spec[1] == TType.MAP:
        if spec[3][2] == TType.STRUCT:
            ttype = spec[3][3][0].__name__
        else:
            ttype = type_map[spec[3][2]]

        return "(dict, {0}, {1})".format(type_map[spec[3][0]], ttype)
    else:
        return type_map[spec[1]]

optional_re = "{0:d}: +optional +[a-z0-9<>_-]+ +{1}"


def main():

    enums = []
    classes = []

    thrift_path = os.path.join(path, "pyload.thrift")
    with io.open(thrift_path, mode='rb') as fp:
        tf = fp.read()

    print("generating apitypes.py")

    for name in dir(ttypes):
        klass = getattr(ttypes, name)

        if name in ("TBase", "TExceptionBase") or name.startswith("_") or not (
                issubclass(klass, ttypes.TBase) or issubclass(klass, ttypes.TExceptionBase)):
            continue

        if hasattr(klass, "thrift_spec"):
            classes.append(klass)
        else:
            enums.append(klass)

    apitypes_path = os.path.join(path, "apitypes.py")
    apitypes_debug_path = os.path.join(path, "apitypes_debug.py")
    with nested(io.open(apitypes_path, mode='wb'), io.open(apitypes_debug_path, mode='wb')) as (f, dev):
        fp.write("""# -*- coding: utf-8 -*-
# Autogenerated by pyload
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING


class BaseObject(object):
\t__version__ = {0}
\t__slots__ = []

\tdef __str__(self):
\t\treturn "<{0} {1}>".format(self.__class__.__name__, ", ".join("{0}={1}".format(k, getattr(self, k)) for k in self.__slots__))


class ExceptionObject(Exception):
\t__version__ = {0}
\t__slots__ = []

""".format(info().version))

        dev.write("""# -*- coding: utf-8 -*-
# Autogenerated by pyload
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING\n
from pyload.core.datatype import *\n
""")

        dev.write("enums = [\n")

        # generate enums
        for enum in enums:
            name = enum.__name__
            fp.write("class {0}:\n".format(name))

            for attr in sorted(dir(enum), key=lambda x: getattr(enum, x)):
                if attr.startswith("_") or attr in ("read", "write"):
                    continue
                fp.write("\t{0} = {1}\n".format(attr, getattr(enum, attr)))

            dev.write("\t\"{0}\",\n".format(name))
            fp.write("\n")

        dev.write("]\n\n")

        dev.write("classes = {\n")

        for klass in classes:
            name = klass.__name__
            base = "ExceptionObject" if issubclass(
                klass, ttypes.TExceptionBase) else "BaseObject"
            fp.write("class {0}({1}):\n".format(name, base))

            # No attributes, do not write further info
            if not klass.__slots__:
                fp.write("\tpass\n\n")
                continue

            fp.write("\t__slots__ = {0}\n\n".format(klass.__slots__))
            dev.write("\t'{0}' : [".format(name))

            # create init
            args = ['self'] + ["{0}=None".format(x) for x in klass.__slots__]
            specs = []

            fp.write("\tdef __init__({0}):\n".format(", ".join(args)))
            for i, attr in enumerate(klass.__slots__):
                fp.write("\t\tself.{0} = {1}\n".format(attr, attr))

                spec = klass.thrift_spec[i + 1]
                # assert correct order, so the list of types is enough for
                # check
                assert spec[2] == attr
                # dirty way to check optional attribute, since it is not in the generated code
                # can produce false positives, but these are not critical
                optional = re.search(
                    optional_re.format(
                        i + 1, attr), tf, flags=re.I)
                if optional:
                    specs.append("(None, {0})".format(get_spec(spec)))
                else:
                    specs.append(get_spec(spec))

            fp.write("\n")
            dev.write(", ".join(specs) + "],\n")

        dev.write("}\n\n")

        fp.write("class Iface(object):\n")
        dev.write("methods = {\n")

        for name in dir(Pyload.Iface):
            if name.startswith("_"):
                continue

            func = inspect.getargspec(getattr(Pyload.Iface, name))

            fp.write("\tdef {0}({1}):\n\t\tpass\n".format(
                name, ", ".join(func.args)))

            spec = getattr(Pyload, "{0}_result".format(name)).thrift_spec
            if not spec or not spec[0]:
                dev.write("\t'{0}': None,\n".format(name))
            else:
                spec = spec[0]
                dev.write("\t'{0}': {1},\n".format(name, get_spec(spec)))

        fp.write("\n")
        dev.write("}\n")


if __name__ == '__main__':
    main()
