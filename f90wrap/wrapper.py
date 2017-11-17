#!/Users/Yann/anaconda/bin/python
"""
# HF XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# HF X
# HF X   f90wrap: F90 to Python interface generator with derived type support
# HF X
# HF X   Copyright James Kermode 2011-2014
# HF X
# HF X   These portions of the source code are released under the GNU General
# HF X   Public License, version 2, http://www.gnu.org/copyleft/gpl.html
# HF X
# HF X   If you would like to license the source code under different terms,
# HF X   please contact James Kermode, james.kermode@gmail.com
# HF X
# HF X   When using this software, please cite the following reference:
# HF X
# HF X   http://www.jrkermode.co.uk/f90wrap
# HF X
# HF XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
"""
from __future__ import print_function

import os
import sys
import traceback
import copy
import logging
import pprint
import warnings

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from f90wrap import __version__

from f90wrap import parser as fparse
from f90wrap import fortran
from f90wrap.sizeof_fortran_t import sizeof_fortran_t
from f90wrap import transform as tf

from f90wrap import f90wrapgen as fwrap
from f90wrap import pywrapgen as pywrap
from f90wrap.pruning import prune

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

def main(argv=None):
    '''Parse and wrap Fortran 90 code, including derived types.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_version_message = '%%(prog)s %s' % program_version
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

   Copyright James Kermode 2011-2017

   These portions of the source code are released under the GNU General
   Public License, version 2, http://www.gnu.org/copyleft/gpl.html

   If you would like to license the source code under different terms,
   please contact James Kermode, james.kermode@gmail.com

   When using this software, please cite the following reference:

   http://www.jrkermode.co.uk/f90wrap

USAGE
''' % program_shortdesc

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        parser.add_argument("files", nargs="+", help="The files to include in the wrap")
        parser.add_argument("--pydest", default=".", help="folder to store python files generated")
        parser.add_argument("--fdest", default=".", help="folder to store fortran files generated")
        parser.add_argument('-p', '--prefix',
                            help="""Prefix to prepend to arguments and subroutines.""",
                            default='f90wrap_')
        parser.add_argument('-c', '--callback', nargs="*", default=[],
                            help="""Names of permitted callback routines.""")
        parser.add_argument('-C', '--constructors', nargs="*",  default=('initialise_ptr', 'initialise', 'allocate'),
                            help="""Names of constructor routines.""")
        parser.add_argument('-D', '--destructors', nargs="*", default=('finalise', 'deallocate'),
                            help="""Names of destructor routines.""")
        parser.add_argument('-k', '--kind-map',
                            help="""File containting Python dictionary in f2py_f2cmap format""")
        parser.add_argument('-s', '--string-lengths',
                            help=""""File containing Python dictionary mapping string length names to values""")
        parser.add_argument('-S', '--default-string-length', default=1024, type=int,
                            help="""Default length of character strings""")
        parser.add_argument('-i', '--init-lines',
                            help="""File containing Python dictionary mapping type names to necessary initialisation code""")
        parser.add_argument('-I', '--init-file',
                            help="""Python source file containing code to be added to autogenerated __init__.py""")
        parser.add_argument('-A', '--argument-name-map',
                            help="""File containing Python dictionary to rename Fortran arguments""")
        parser.add_argument('--short-names',
                            help="""File containing Python dictionary mapping full type names to abbreviations""")
        parser.add_argument('--py-mod-names',
                            help="File containing Python dictionary mapping Fortran module names to Python ones")
        parser.add_argument('--class-names',
                            help="File containing Python dictionary mapping Fortran type names to Python classes")
        parser.add_argument('--joint-modules',
                            help="File containing Python dictionary mapping modules defining times to list of additional modules defining methods")
        parser.add_argument('-m', '--mod-name', default='mod',
                            help="Name of output extension module (without .so extension).")
        parser.add_argument('-M', '--move-methods', action='store_true',
                            help="Convert routines with derived type instance as first agument into class methods")
        parser.add_argument('--shorten-routine-names', action='store_true',
                            help="Remove type name prefix from routine names, e.g. cell_symmetrise() -> symmetrise()")
        parser.add_argument('-P', '--package', action='store_true',
                            help="Generate a Python package instead of a single module")
        parser.add_argument('-a', '--abort-func', default='f90wrap_abort',
                            help='Name of Fortran subroutine to invoke if a fatal error occurs')
        parser.add_argument('--default-to-inout', action='store_true', default=False,
                            help="Sets all arguments without intent to intent(inout)")
        parser.add_argument('-r', '--rule', nargs="*", 
                            help="""Files containing rules for defining structures be public or private""")
        parser.add_argument("--conf-file", help="Use Python configuration script to set options")

        args = parser.parse_args()

        if args.verbose:
            logging.root.setLevel(logging.DEBUG)
        else:
            logging.root.setLevel(logging.INFO)

        # set defaults, to be overriden by command line args and config file
        kind_map = {}
        short_names = {}
        string_lengths = {}
        init_lines = {}
        py_mod_names = {}
        class_names = {}
        argument_name_map = {}
        only = None
        skip = None
        joint_modules = {}
        callback = []
        remove_optional_arguments = []

        # bring command line arguments into global scope so we can override them
        globals().update(args.__dict__)

        # read command line arguments
        if args.kind_map:
            kind_map = eval(open(args.kind_map).read())
        constructors = args.constructors
        destructors = args.destructors

        if args.short_names:
            short_names = eval(open(args.short_names).read())

        if args.string_lengths:
            string_lengths = eval(open(args.string_lengths).read())

        if args.init_lines:
            init_lines = eval(open(args.init_lines).read())

        if args.py_mod_names:
            py_mod_names = eval(open(args.py_mod_names).read())

        if args.class_names:
            class_names = eval(open(args.class_names).read())

        if args.argument_name_map:
            argument_name_map = eval(open(args.argument_name_map).read())

        if args.joint_modules:
            joint_modules = eval(open(args.joint_modules).read())

        # finally, read config file, allowing it to override command line args
        if args.conf_file:
            print("Executing config file %s" % args.conf_file)
            exec(open(args.conf_file).read())

        print('Kind map (also saved to .f2py_f2cmap)')
        pprint.pprint(kind_map)
        f2py_f2cmap = open('.f2py_f2cmap', 'w')
        pprint.pprint(kind_map, f2py_f2cmap)
        f2py_f2cmap.close()
        print()

        print('Constructors:')
        print(constructors)
        print()

        print('Destructors:')
        print(destructors)
        print()

        print('Short names for derived types:')
        pprint.pprint(short_names)
        print()

        print('String lengths:')
        pprint.pprint(string_lengths)
        print()

        print('Initialisation lines for derived types')
        pprint.pprint(init_lines)
        print()

        print('Python module name remapping')
        pprint.pprint(py_mod_names)

        print('Class names remapping')
        pprint.pprint(class_names)
        print()

        print('Argument name map:')
        pprint.pprint(argument_name_map)
        print()

        fsize = sizeof_fortran_t()
        print('Size of Fortran derived type pointers is %d bytes.' % fsize)
        print()

        # parse input Fortran source files
        print('Parsing Fortran source files %r ...' % args.files)
        files_not_found = [file for file in args.files if not os.path.exists(file)]
        if len(files_not_found) != 0:
            raise Exception("source file '%s' not exist" % (','.join(files_not_found)))
        parse_tree = fparse.read_files(args.files)
        print('done parsing source.')
        print()
        tree = copy.deepcopy(parse_tree)
        
        if rule and len(rule) != 0:
            files_not_found = [file for file in rule if not os.path.exists(file)]
            if len(files_not_found) != 0:
                raise Exception("pruning rule file '%s' not exist" % (','.join(files_not_found)))
            tree = prune(tree, rule)

        types = fortran.find_types(tree)
        print('Derived types detected in Fortran source files:')
        pprint.pprint(types)
        print()

        for type_name, typ in types.items():
            class_names[type_name] = typ.orig_name
        print('Class name mapping:')
        pprint.pprint(class_names)

        modules_for_type = {}
        for type_name, typ in types.items():
            modules_for_type[typ.mod_name] = typ.mod_name
        modules_for_type.update(joint_modules)
        print('Modules for each type:')
        pprint.pprint(modules_for_type)

        tree = tf.transform_to_generic_wrapper(tree,
                                               types,
                                               callback,
                                               constructors,
                                               destructors,
                                               short_names,
                                               init_lines,
                                               argument_name_map,
                                               move_methods,
                                               shorten_routine_names,
                                               modules_for_type,
                                               remove_optional_arguments)

        py_tree = copy.deepcopy(tree)
        f90_tree = copy.deepcopy(tree)

        py_tree = tf.transform_to_py_wrapper(py_tree, types)

        f90_tree = tf.transform_to_f90_wrapper(f90_tree, types,
                                               callback,
                                               constructors,
                                               destructors,
                                               short_names,
                                               init_lines,
                                               string_lengths,
                                               default_string_length,
                                               sizeof_fortran_t=fsize,
                                               kind_map=kind_map)

        pywrap.PythonWrapperGenerator(prefix, mod_name,
                                      types, make_package=package,
                                      kind_map=kind_map,
                                      init_file=args.init_file,
                                      py_mod_names=py_mod_names,
                                      class_names=class_names,
                                      dest = pydest).visit(py_tree)
        fwrap.F90WrapperGenerator(prefix, fsize, string_lengths,
                                  abort_func, kind_map, types, default_to_inout,
                                  dest = fdest).visit(f90_tree)
        return 0

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0

    except Exception as e:
        traceback.print_exc()
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        if 'args' in locals() and args.verbose:
            raise
        else:
            return 2