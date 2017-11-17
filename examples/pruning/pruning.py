"""
Created on Fri May 26 11:01:18 2017
@author: yagweb
""" 
from __future__ import print_function

import os
import copy
import pprint
import warnings

from f90wrap import parser as fparse
from f90wrap import fortran
from f90wrap.sizeof_fortran_t import sizeof_fortran_t
from f90wrap import transform as tf

from f90wrap import f90wrapgen as fwrap
from f90wrap import pywrapgen as pywrap
from f90wrap.pruning import PruningRuleFile
from f90wrap.wrapper import main
    
def test_parser():
    file = PruningRuleFile('pruning_rules')
    file.dump()
    
def compile_lib(files):
    obj_files = [os.path.splitext(os.path.basename(bb))[0]+".o" for bb in files]
    f90 = r'"C:\Program Files\mingw-w64\x86_64-7.1.0-posix-seh-rt_v5-rev0\mingw64\bin\gfortran.exe"'
    f90 = r'gfortran'
    for src, obj in zip(files, obj_files): 
        cmd = "%s -m64 -x f95-cpp-input -fPIC -c %s -o %s" % (f90, src, obj)
        print(cmd)
        os.system(cmd)
    cmd = "ar -rcs libsrc.a %s" % (" ".join(obj_files))
    print(cmd)
    os.system(cmd)

def gene_wrap_files(files):   
    import sys
    sys.argv.extend(files)
    sys.argv.extend(["-m", "demo"])
    sys.argv.extend(["--fdest", "tmp"])
    sys.argv.extend(["--pydest", "."])
    sys.argv.extend(["-p", "f90wrap_"])
    sys.argv.extend(["-k", "kind_map"])
#    sys.argv.extend(["-r", "pruning_rules"])
    main()
        
def compile_ext():
    import glob
    import platform
    sysstr = platform.system()
    if(sysstr == "Windows"):
        files = glob.glob('tmp/f90wrap_*.f90')#windows cmd not support wildcard
        cc = '--compiler=mingw32'
    else:
        files = 'tmp/f90wrap_*.f90'
        cc = ''
    mod_name = "_demo"
    f2py = os.path.abspath("../../scripts/f2py-f90wrap")
    # --compiler=mingw32  #symbol table not found
    cmd = "python {f2py} {cc} --fcompiler=gfortran --verbose ".format(f2py = f2py, cc = cc) + \
    "--build-dir . -c -m {mod_name} -L. -lsrc {files}".format(mod_name = mod_name, files = " ".join(files))
    print(cmd)
    os.system(cmd)

def test():
    import demo
    b = 1
    a = demo.entity.hello()
    print(a)
    a = demo.entity.hello2(10)
    print(a) 
    print(dir(demo.logical_test))
    a = demo.logical_test(1)
    print(a)
    
def test_kind():
    kind_map = eval(open('kind_map').read())
    from f90wrap.fortran import normalise_type, f2py_type, f2c_type
    _type = 'real(dp)'.lower()
    _type = 'LOGICAL(C_BOOL)'.lower()
    print(_type)
    aa = normalise_type(_type.lower(), kind_map)
    print(aa)    
    aa = f2py_type(_type.lower(), kind_map)
    print(aa)    
    aa = f2c_type(_type.lower(), kind_map)
    print(aa)    
    
if __name__ == "__main__":
#    test_parser()
    files = [
             'entity.f90',
             'test.f90',
             'routine.f90',
            ]
#    compile_lib(files)
#    gene_wrap_files(files)
#    compile_ext()
#    test()
    test_kind()