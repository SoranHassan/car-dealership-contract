# ui/__init__.py
from .app import App, SearchApp
from .license_manager import license_check
from .sync_service import SyncService

# برای جلوگیری از circular import، Ui_MainWindow رو اینجا نیار
# اون مستقیم از ui.py import بشه

__all__ = ['App', 'SearchApp', 'license_check', 'SyncService']