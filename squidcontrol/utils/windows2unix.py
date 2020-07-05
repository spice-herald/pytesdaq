import sys
import os

if len(sys.argv) != 2:
    print('Convert a text file from Windows (\\r\\n for new line to \\n).')
    print('Run: python windows2unix.py filename')
    sys.exit()

fn = sys.argv[1]
f_in = open(fn, 'r')
f_out = open(fn + '_2', 'w')

for line in f_in.readlines():
    f_out.write(line)

f_out.close()
f_in.close()

os.rename(fn + '_2', fn)
