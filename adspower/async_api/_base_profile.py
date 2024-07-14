from abc import ABC, abstractmethod
from typing import Optional, AsyncContextManager
from adspower.async_api import ProfileAPI, Group
from contextlib import asynccontextmanager


class _BaseProfile(ProfileAPI, ABC):
    async def __aenter__(self):
        browser = await self.get_browser()
        return browser

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.quit()

    @classmethod
    @asynccontextmanager
    async def anonymous(cls, group: Group) -> AsyncContextManager:
        profile = await cls.create(group=group)
        try:
            yield await profile.get_browser()
        finally:
            await profile.quit()
            await profile.delete()

    @property
    @abstractmethod
    def browser(self):
        pass

    @abstractmethod
    async def get_browser(
            self,
            ip_tab: bool = False,
            new_first_tab: bool = True,
            launch_args: Optional[list[str]] = None,
            headless: bool = False,
            disable_password_filling: bool = False,
            clear_cache_after_closing: bool = False,
            enable_password_saving: bool = False,
            close_tabs: bool = True,
    ):
        pass

    @abstractmethod
    def close_tabs(self) -> None:
        pass

    @abstractmethod
    async def quit(self) -> None:
        pass
