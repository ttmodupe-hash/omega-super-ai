"""International Tax Module — Omega Super AI v10"""
import gzip
import base64
import types

# Import all data parts
from omega.td0 import P as _P0
from omega.td1 import P as _P1
from omega.td2 import P as _P2
from omega.td3 import P as _P3
from omega.td4 import P as _P4
from omega.td5 import P as _P5
from omega.td6 import P as _P6
from omega.td7 import P as _P7
from omega.td8 import P as _P8
from omega.td9 import P as _P9

_ENCODED = _P0 + _P1 + _P2 + _P3 + _P4 + _P5 + _P6 + _P7 + _P8 + _P9
_DECOMPRESSED = gzip.decompress(base64.b64decode(_ENCODED))

_exec_ns = {"__name__": "omega.tax_module", "__file__": __file__}
exec(compile(_DECOMPRESSED, "<tax_module>", "exec"), _exec_ns)
InternationalTax = _exec_ns["InternationalTax"]
__all__ = ["InternationalTax"]
