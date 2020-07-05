import os
import glob

get_files = glob.glob('get*.cpp')
set_files = glob.glob('set*.cpp')
filenames = get_files + set_files
filenames = sorted(filenames)

compile_fn = open('compile_all.bat', 'w')
for fn in filenames:
    compile_fn.write('cl /EHsc %s magsv.lib\n' % fn)

compile_fn.close()


