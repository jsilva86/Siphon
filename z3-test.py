from z3 import *
import re

solver = Solver()

x = FP("x", FPSort(8, 24))

print(fpLT(x, 5))
