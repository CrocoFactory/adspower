"""
adspower
~~~~~~~~~~~~~~
The package for interacting with anti-detect browser APIs.
Author's github - https://github.com/blnkoff

Usage example:
   >>> from adspower.sync_api.selenium import Profile, Group
   >>> my_group = Group.query(name='my_group')[0]
   >>> profile = Profile.create(group=my_group, name='my_profile')
   >>>
   >>> with profile as browser:
   >>>      browser.get('https://github.com/blnkoff/adspower')
:copyright: (c) 2023 by Alexey
:license: Apache 2.0, see LICENSE for more details.
"""

from adspower.types import FingerprintConfig, ProxyConfig
