from gi.repository import Gtk
from typing import Callable


PREFER_DARK_THEME_PROPERTY = "gtk-application-prefer-dark-theme"


class PreferDarkThemeListener:
    def __init__(self) -> None:
        self.settings: Gtk.Settings = Gtk.Settings.get_default()
        self.callbacks: list[Callable[..., None]] = []
        if self.settings:
            self.settings.connect(
                f"notify::{PREFER_DARK_THEME_PROPERTY}",
                self._on_theme_changed,
            )
        self._notify_current_mode()

    def _on_theme_changed(self, settings: Gtk.Settings, param: str) -> None:
        self._notify_current_mode()

    def _notify_current_mode(self) -> None:
        for callback in self.callbacks:
            callback(prefers_dark_mode=self.prefers_dark_mode)

    @property
    def prefers_dark_mode(self) -> bool:
        return bool(self.settings.get_property(PREFER_DARK_THEME_PROPERTY))

    def register_callback(self, callback: Callable[[bool], None]) -> None:
        """
        Register a callback to be invoked when the dark/light mode changes.

        The callback will receive a single positional argument indicating
        whether dark mode is enabled (True) or light mode (False).
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            callback(self.prefers_dark_mode)
