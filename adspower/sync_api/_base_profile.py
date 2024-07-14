from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, ContextManager
from adspower.sync_api import ProfileAPI, Group


class _BaseProfile(ProfileAPI, ABC):
    def __enter__(self):
        browser = self.get_browser()
        return browser

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()

    @classmethod
    @contextmanager
    def anonymous(cls, group: Group) -> ContextManager:
        profile = cls.create(group=group)
        try:
            yield profile.get_browser()
        finally:
            profile.quit()
            profile.delete()

    @property
    @abstractmethod
    def browser(self):
        pass

    @abstractmethod
    def get_browser(
            self,
            ip_tab: bool = False,
            new_first_tab: bool = True,
            launch_args: Optional[list[str]] = None,
            headless: bool = False,
            disable_password_filling: bool = False,
            clear_cache_after_closing: bool = False,
            enable_password_saving: bool = False,
            close_tabs: bool = True
    ):
        pass

    @abstractmethod
    def close_tabs(self) -> None:
        pass

    @abstractmethod
    def quit(self) -> None:
        pass
