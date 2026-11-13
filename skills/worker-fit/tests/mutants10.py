"""The mutant runner moved to mutants11.py, which carries every mutant of this file (anchors updated for the field-profile code),
the new ones, and a non-zero exit status on any survivor or NOT-APPLIED mutant. This stub runs it with the same arguments."""
import os, runpy, sys
sys.argv[0] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutants11.py")
runpy.run_path(sys.argv[0], run_name="__main__")
