"""
adspower
~~~~~~~~~~~~~~
The package for interacting with anti-detect browser APIs.
Author's github - https://github.com/blnkoff

Usage example:
   >>> from adspower import AdsPower
   >>> ads_power = AdsPower('ja54rwh')
   >>> with ads_power as driver:
   >>>      driver.get('https://github.com/blnkoff/adspower')
:copyright: (c) 2023 by Alexey
:license: Apache 2.0, see LICENSE for more details.
"""

__version__ = "1.0.0"

from .adspower import AdsPower
from .types import (UserProxyConfig, FingerprintConfig, CreateProfileParams, QueryProfilesParams, QueryGroupParams,
                    GroupInfo, ProfileInfo)
