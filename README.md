# adspower

[![Croco Logo](https://i.ibb.co/G5Pjt6M/logo.png)](https://t.me/crocofactory)


The package for interacting with API of anti-detect browser AdsPower.

- **[Telegram channel](https://t.me/crocofactory)**
- **[Bug reports](https://github.com/blnkoff/ether-wallet/issues)**

adspower's source code is made available under the [MIT License](LICENSE)
             
# Restrictions
1. During using the package, AdsPower must be opened. 
2. The local API is available only in paid AdsPower subscriptions
3. AdsPower has frequency control for all APIs, max. access frequency: 1 request/second 

# Quick start

For example, you can use driver by the following way.

```python
from adspower import AdsPower
ads_power = AdsPower('ja54rwh')
with ads_power as driver:
  driver.get('https://github.com/blnkoff/adspower')
```

Here is example of usage of creating profiles from proxies

```python
from adspower import AdsPower, CreateProfileParams, UserProxyConfig

def create_profiles(config: dict[str], proxies) -> list[AdsPower]:
    group_name = config['ads_power']['group_name']

    group_id = AdsPower.query_group(group_name=group_name)[0]['group_id']

    data_set = []
    for proxy in proxies:
        proxy_config = UserProxyConfig(
            proxy_soft='other',
            proxy_type=proxy.type,
            proxy_host=proxy.host,
            proxy_port=proxy.port,
            proxy_user=proxy.login,
            proxy_password=proxy.password
        )
        data_set.append(CreateProfileParams(group_id=group_id, user_proxy_config=proxy_config))

    profiles = []
    for data in data_set:
        profiles.append(AdsPower.create_profile(data))

    return profiles
```

Here is example of retrieving profiles from AdsPower

```python
from adspower import AdsPower

def retrieve_profiles(config: dict[str]):
    group_name = config['ads_power']['group_name']

    group_id = AdsPower.query_group(group_name=group_name)['group_id']

    response = AdsPower.query_profiles(group_id=group_id)

    profiles = [AdsPower(profile['user_id']) for profile in response]
    return profiles
```

# Installing adspower
To install the package from GitHub you can use that:
```sh
pip install git+https://github.com/blnkoff/adspower.git
```

To install the package from PyPi you can use that:
```sh
pip install adspower
```
