"""International Tax Module — Omega Super AI v10
Auto-generated loader — decompresses and loads the full tax module.
"""
import gzip
import base64
import sys
import types

# Import data chunks
from omega.tax_data1 import CHUNK as _C1
from omega.tax_data2 import CHUNK as _C2
from omega.tax_data3 import CHUNK as _C3

# Reassemble, decompress, and execute
_ENCODED = _C1 + _C2 + _C3
_DECOMPRESSED = gzip.decompress(base64.b64decode(_ENCODED))

# Create module namespace
_mod = types.ModuleType("omega.tax_module")
_mod.__file__ = __file__
_exec_ns = {"__name__": "omega.tax_module", "__file__": __file__}
exec(compile(_DECOMPRESSED, "<tax_module>", "exec"), _exec_ns)

# Extract the InternationalTax class
InternationalTax = _exec_ns["InternationalTax"]

# Make available from this module
__all__ = ["InternationalTax"]
