"""
Test ability to use matlab engine to talk to the anmodel.
"""
import os
import matlab.engine
import fnmatch


def find_files(directory, pattern):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


# we need to find the 'testANModel.m" file and go to it's directory:
matches = []
currentpath = os.getcwd()
print currentpath
mfn = ''
for fn in find_files(os.path.join(currentpath,'cnmodel', 'an_model'), 'testANmodel.m'):
    mfn = fn
print mfn
exit(1)

eng = matlab.engine.start_matlab()

eng.cd('/Users/pbmanis/Desktop/Python/cnmodel/cnmodel/an_model')  # must run from within the directory
eng.testANModel(nargout=0)
eng.quit()
os.chdir(currentpath)