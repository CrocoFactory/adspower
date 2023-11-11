import pytest
from adspower import AdsPower


@pytest.fixture
def group_id():
    return AdsPower.query_group(group_name='test')['group_id']


def test_create_profile(group_id):
    assert AdsPower.create_profile(group_id=group_id)


def test_get_driver(group_id):
    ads_power = AdsPower.create_profile(group_id=group_id)
    driver = ads_power.get_driver()
    driver.get('https://google.com')


def test_wait_for_delay(group_id):
    for _ in range(5):
        assert AdsPower.query_group(group_name='test')[-1]['group_id']
