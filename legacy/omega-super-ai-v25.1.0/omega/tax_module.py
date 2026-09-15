"""International Tax Module — Omega Super AI v10
Auto-generated loader — decompresses and loads the full tax module.

NOTE: This module requires tax_data1.py, tax_data2.py, and tax_data3.py
to be present in the same directory. Download the complete release zip
from the repository if these files are missing.
"""
import gzip
import base64
import types

# Import data chunks (3 parts)
from omega.tax_data1 import CHUNK as _C1
from omega.tax_data2 import CHUNK as _C2
from omega.tax_data3 import CHUNK as _C3

# Reassemble, decompress, and execute
_ENCODED = _C1 + _C2 + _C3
_DECOMPRESSED = gzip.decompress(base64.b64decode(_ENCODED))

_exec_ns = {"__name__": "omega.tax_module", "__file__": __file__}
exec(compile(_DECOMPRESSED, "<tax_module>", "exec"), _exec_ns)

InternationalTax = _exec_ns["InternationalTax"]
__all__ = ["InternationalTax"]
