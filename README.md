# adspower
                     
<a href="https://www.adspower.com"><h1 align="center"><img src="https://raw.githubusercontent.com/CrocoFactory/adspower/main/branding/adspower/banner.png" width="300" style="border-radius:7px;"></h1><br></a>

[![Python versions](https://img.shields.io/pypi/pyversions/adspower?color=%231D4DFF)](https://pypi.org/project/adspower/)
[![PyPi Version](https://img.shields.io/pypi/v/adspower?color=%231D4DFF)](https://pypi.org/project/adspower/)


The package for interacting with API of anti-detect browser [AdsPower](https://www.adspower.com).

- **[Overview](#quick-start)**
- **[Installing](#installing-adspower)**
- **[Bug reports](https://github.com/CrocoFactory/adspower/issues)**

The project is made by the **[Croco Factory](https://github.com/CrocoFactory)** team

adspower's source code is made available under the [MIT License](LICENSE)
         
## Features
- Synchronous and asynchronous interaction with the local API
- Interaction with the most popular libraries for browser automation in Python: Selenium and Playwright

## Restrictions
1. During using the package, AdsPower must be opened. 
2. The local API is available only in paid AdsPower subscriptions
3. AdsPower has frequency control for all APIs, max. access frequency: 1 request/second 


## Quick start

*Example of interacting with synchronous API.*

```python
from adspower.sync_api import Group, ProfileAPI
group = Group.create(name='my_group', remark='The best group ever')

profile_api = ProfileAPI.create(group=group)  
print(f'Profile {profile_api.name} was created in group {group.name}')
```

**Use `ProfileAPI` only when** you don't need `Selenium` and `Playwright` interactions.

Library provides ways to interact the most popular libraries for browser automation in Python: `Selenium` and `Playwright`.
To get a browser, you can use `with` statement:

- *Selenium*

```python
from adspower.sync_api.selenium import Profile, Group
my_group = Group.query(name='my_group')[0]
profile = Profile.create(group=my_group, name='my_profile')

with profile as browser:
   browser.get('https://github.com/blnkoff/adspower')
```

- *Playwright*

```python
from adspower.async_api.playwright import Profile, Group

async def main() -> None:
    my_group = (await Group.query(name='my_group'))[0]
    profile = await Profile.create(group=my_group, name='my_profile')
    
    async with profile as browser:
       page = browser.pages[0]
       await page.goto('https://github.com/blnkoff/adspower')
```

Both versions support sync and async API.

Or manually call `get_browser` if you need specify part of behaviour.
```python
from adspower.sync_api.selenium import Profile, Group

my_group = Group.query(name='my_group')[0]
profile = Profile.create(group=my_group, name='my_profile')
browser = profile.get_browser(ip_tab=False, headless=True, disable_password_filling=True)
browser.get('https://github.com/blnkoff/adspower')
profile.quit()
```

Notice that you must not call quitting methods of `Playwright` library or `Selenium` after `profile.quit()`, since 
it calls these methods automatically. An attempt to do so will lead to the error.
           
*Example of setting proxy and fingerprint*

```python
from adspower.sync_api.playwright import Profile, Group
from adspower import ProxyConfig, FingerprintConfig

proxy = ProxyConfig(
    soft='other',
    type='http',
    host='xx.xx.x.xx',
    port=1000,
    user='username',
    password='password'
)

fingerprint = FingerprintConfig(
    ua='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.112 Safari/537.36'
)

group = Group.query(name='my_group')[0]
profile = Profile.create(group=group, proxy_config=proxy, name='my_profile', fingerprint_config=fingerprint)
```

There are extension categories, implemented as `Category` class. At the moment, it can`t be created, but can be retrieved.
You can manually create extension category and used it for profile creation using API.
  
*Example of querying category* 

```python
from adspower.sync_api.playwright import Profile, Category, Group

category = Category.query(name='my_category')[0]
group = Group.query(name='my_group')[0]

profile = Profile.create(group=group, category=category)
```

You can create anonymous profile that is deleted after last statement in context manager.
   
*Example of anonymous profile*
```python
from adspower.async_api.playwright import Profile, Group

async def main() -> None:
    my_group = (await Group.query(name='my_group'))[0]
    profile = await Profile.anonymous(group=my_group)

    async with profile as browser:
        page = browser.pages[0]
        await page.goto('https://www.google.com')
```

Each API entity, such as Profile, Group and Category, pretty formatted, can be compared and converted to dict
     
*Example 1*

```python
from adspower.sync_api.playwright import Category

category = Category.query(name='my_category')[0]
print(category) 
```

```markdown
Category(id=10515; name=my_category)
```
  
*Example 2*

```python
from adspower.sync_api.playwright import Profile, Group

group = Group.query(name='my_group')[0]
profile_created = Profile.create(group=group)

profile_queried = Profile.query(id_=profile_created.id)
print(profile_queried == profile_created)
```

```python
True
```

*Example 3*
```python
from adspower.sync_api.playwright import Category

category = Category.query(name='my_category')[0]
print(category.to_dict())
```

```json
{
    "id": 10515, 
    "name": "my_category", 
    "remark": "category remark"
}
```

# Installing adspower
To install the package from PyPi you can use that:

```sh
pip install adspower
```

You will probably want to use the pacakge with `Selenium` or `Playwright`. You can install it as extra-package:

```sh
pip install adspower[playwright]
```

```sh
pip install adspower[selenium]
```
