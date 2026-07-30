import sys, os
sys.path.insert(0, os.path.abspath('..'))
try:
    import algorithms
    public = [k for k in dir(algorithms) if not k.startswith('_')]
    print('OK, public symbols:', public)
except Exception as e:
    print('IMPORT ERROR:', e)
    import traceback
    traceback.print_exc()
