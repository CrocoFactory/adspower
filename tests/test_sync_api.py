from typing import Callable
import pytest
from selenium.webdriver.chrome.webdriver import WebDriver
from adspower.sync_api import Group, Category, HTTPClient
from adspower.sync_api.selenium import Profile as ProfileSelenium
from adspower.sync_api.playwright import Profile as ProfilePlaywright

HTTPClient.set_delay(1.1)
ProfileType = ProfileSelenium | ProfilePlaywright


class TestGroup:
    def test_create(self, name, remark):
        group = Group.create(name=name, remark=remark)
        group_to_check = Group.query(name=name)[0]
        assert group == group_to_check

    def test_update(self, name, remark):
        group = Group.create(name=name, remark=remark)
        group.update(name=f'new{name}', remark='new_remark')
        group_to_check = Group.query(name=f'new{name}')[0]
        assert group == group_to_check


class TestCategory:
    def test_query(self, category_name):
        categories = Category.query()
        assert len(categories) > 0


@pytest.mark.parametrize('profile_cls', [ProfileSelenium, ProfilePlaywright])
class TestProfile:
    @pytest.fixture(scope="function")
    def make_profile(
            self,
            profile_cls,
            get_name,
            get_remark
    ) -> Callable[[], tuple[ProfileType, type[ProfileType]]]:
        def _make_profile() -> tuple[ProfileType, type[ProfileType]]:
            group = Group.create(name=get_name(), remark=get_remark())
            profile = profile_cls.create(name=get_name(), remark=get_remark(), group=group)
            return profile, profile_cls

        return _make_profile

    def test_create(self, make_profile):
        profile, profile_cls = make_profile()

        profile_to_check = profile_cls.query(id_=profile.id)[0]
        assert profile == profile_to_check

    def test_update(self, make_profile, name, remark):
        profile, profile_cls = make_profile()

        profile.update(name=f'new{name}')
        profile_to_check = profile_cls.query(id_=profile.id)[0]
        assert profile == profile_to_check

    def test_delete(self, make_profile):
        profile, profile_cls = make_profile()
        profile.delete()

        try:
            query = profile_cls.query(id_=profile.id)[0]
            assert not query
        except IndexError:
            pass

    def test_move(self, make_profile, name, remark):
        profile, profile_cls = make_profile()

        name = profile.group.name
        group = Group.create(name=f'new{name}', remark=remark)

        group_id_before = profile.group.id

        profile.move(group=group)
        assert group_id_before != profile.group.id

    def test_get_browser(self, make_profile):
        profile, profile_cls = make_profile()

        with profile as browser:
            if isinstance(browser, WebDriver):
                browser.get('https://google.com')
            else:
                page = browser.pages[0]
                page.goto('https://google.com')
