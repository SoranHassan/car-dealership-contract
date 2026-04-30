# tests/test_license.py - نسخه نهایی اصلاح شده
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock


class TestLicenseManager:
    
    def test_license_check_fail_no_file(self):
        """تست بررسی لایسنس بدون فایل"""
        with patch('ui.license_manager.os.path.exists', return_value=False):
            from ui.license_manager import check_license
            result = check_license()
            assert result is False
    
    def test_save_and_check_license(self):
        """تست ذخیره و بررسی لایسنس"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('ui.license_manager.get_license_path', return_value=os.path.join(tmpdir, "license.key")):
                with patch('ui.license_manager.get_system_uuid', return_value="test-uuid-456"):
                    from ui.license_manager import save_license, check_license
                    
                    result = save_license("test-uuid-456")
                    assert result is True
                    
                    result = check_license()
                    assert result is True
    
    def test_get_system_uuid(self):
        """تست گرفتن UUID سیستم"""
        from ui.license_manager import get_system_uuid
        
        uuid_val = get_system_uuid()
        if uuid_val is not None:
            assert isinstance(uuid_val, str)
            assert len(uuid_val) > 0
    
    @patch('ui.license_dialog.LicenseDialog')  # تغییر: از license_dialog import کن
    @patch('ui.license_manager.get_system_uuid')
    def test_license_check_with_correct_key(self, mock_get_uuid, mock_dialog_class):
        """تست فعال‌سازی با کلید صحیح"""
        from ui.license_manager import license_check
        
        mock_get_uuid.return_value = "test-uuid-789"
        
        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = 1
        mock_dialog_instance.get_key.return_value = "@Soran9978"
        mock_dialog_class.return_value = mock_dialog_instance
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('ui.license_manager.get_license_path', return_value=os.path.join(tmpdir, "license.key")):
                result = license_check()
                assert result is True
    
    @patch('ui.license_dialog.LicenseDialog')  # تغییر: از license_dialog import کن
    def test_license_check_with_wrong_key(self, mock_dialog_class):
        """تست فعال‌سازی با کلید اشتباه"""
        from ui.license_manager import license_check
        
        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = 1
        mock_dialog_instance.get_key.return_value = "wrong-key"
        mock_dialog_class.return_value = mock_dialog_instance
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('ui.license_manager.get_license_path', return_value=os.path.join(tmpdir, "license.key")):
                result = license_check()
                assert result is False