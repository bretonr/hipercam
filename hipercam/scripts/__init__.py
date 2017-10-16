"""
command line scripts

All the command line scripts in hipercam are accessed through entry points as
function. This allows them to be included more naturally within the overall
package. Note that the commands 'cadd', 'csub', 'cmul' and 'cdiv' are all
carried out by 'carith'.

The list of functions is a complete list of available scripts. See the
documentation on hipercam.cline for how to supply the arguments on the command
line.
"""

from .arith import add, div, mul, sub
from .carith import cadd, cdiv, cmul, csub
from .combine import combine
from .grab import grab
from .hplot import hplot
from .makestuff import makedata, makefield
from .reduce import reduce
from .rtplot import rtplot
from .setaper import setaper
from .stats import stats

__all__ = [
    'add', 'div', 'mul', 'sub',
    'cadd', 'cdiv', 'cmul', 'csub', 
    'combine', 'grab', 'hplot', 'makedata', 'makefield', 
    'reduce', 'rtplot', 'setaper', 'stats',
    ]
