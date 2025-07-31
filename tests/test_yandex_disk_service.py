import pytest
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

from app.services.yandex_disk_service import YandexDiskService


@pytest.fixture
def yandex_service():
    return YandexDiskService("test_token")


@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestYandexDiskService:
    @pytest.mark.asyncio
    async def test_upload_file_success(self, yandex_service, temp_file):
        with patch.object(yandex_service.client, "upload") as mock_upload:
            with patch.object(yandex_service, "_ensure_directory_exists", new_callable=AsyncMock) as mock_ensure_dir:
                mock_upload.return_value = None
                mock_ensure_dir.return_value = None
                result = await yandex_service.upload_file(temp_file, "/test/file.txt")
                assert result == "/test/file.txt"
                mock_upload.assert_called_once_with(temp_file, "/test/file.txt", True)
                mock_ensure_dir.assert_called_once_with("/test")

    @pytest.mark.asyncio
    async def test_upload_file_not_exists(self, yandex_service):
        result = await yandex_service.upload_file("nonexistent.txt", "/test.txt")
        assert result is None

    @pytest.mark.asyncio
    async def test_download_file_success(self, yandex_service, temp_file):
        with patch.object(yandex_service.client, "download") as mock_download:
            mock_download.return_value = None
            download_path = temp_file + "_download"
            result = await yandex_service.download_file("/test.txt", download_path)
            assert result is True
            mock_download.assert_called_once_with("/test.txt", download_path)

    @pytest.mark.asyncio
    async def test_get_files_list_success(self, yandex_service):
        mock_file = Mock()
        mock_file.name = "test.txt"
        mock_file.path = "/test.txt"
        mock_file.type = "file"
        mock_file.size = 1024
        with patch.object(yandex_service.client, "listdir") as mock_listdir:
            mock_listdir.return_value = [mock_file]
            files = await yandex_service.get_files_list("/")
            assert len(files) == 1
            assert files[0]["name"] == "test.txt"
            assert files[0]["type"] == "file"
            assert files[0]["size"] == 1024

    @pytest.mark.asyncio
    async def test_create_folder_success(self, yandex_service):
        with patch.object(yandex_service.client, "mkdir") as mock_mkdir:
            mock_mkdir.return_value = None
            result = await yandex_service.create_folder("/test_folder")
            assert result is True
            mock_mkdir.assert_called_once_with("/test_folder")

    @pytest.mark.asyncio
    async def test_delete_file_success(self, yandex_service):
        with patch.object(yandex_service.client, "remove") as mock_remove:
            mock_remove.return_value = None
            result = await yandex_service.delete_file("/test.txt")
            assert result is True
            mock_remove.assert_called_once_with("/test.txt", False)

    @pytest.mark.asyncio
    async def test_get_disk_info_success(self, yandex_service):
        mock_disk_info = Mock()
        mock_disk_info.total_space = 1000000000
        mock_disk_info.used_space = 500000000
        with patch.object(yandex_service.client, "get_disk_info") as mock_get_info:
            mock_get_info.return_value = mock_disk_info
            info = await yandex_service.get_disk_info()
            assert info is not None
            assert info["total_space"] == 1000000000
            assert info["used_space"] == 500000000
            assert info["free_space"] == 500000000

    @pytest.mark.asyncio
    async def test_file_exists_success(self, yandex_service):
        with patch.object(yandex_service.client, "exists") as mock_exists:
            mock_exists.return_value = True
            result = await yandex_service.file_exists("/test.txt")
            assert result is True
            mock_exists.assert_called_once_with("/test.txt")

    def test_format_file_size(self, yandex_service):
        assert yandex_service.format_file_size(0) == "0 Б"
        assert yandex_service.format_file_size(1024) == "1.0 КБ"
        assert yandex_service.format_file_size(1024**2) == "1.0 МБ"
        assert yandex_service.format_file_size(1024**3) == "1.0 ГБ"


@pytest.mark.asyncio
async def test_yandex_upload():
    service = YandexDiskService("test_token")
    with patch.object(service.client, "upload") as mock_upload:
        with tempfile.NamedTemporaryFile() as temp_file:
            temp_file.write(b"test content")
            temp_file.flush()
            result = await service.upload_file(temp_file.name, "/test.txt")
            assert result == "/test.txt"


@pytest.mark.asyncio
async def test_yandex_connection():
    service = YandexDiskService("test_token")
    with patch.object(service.client, "get_disk_info") as mock_info:
        mock_disk = Mock()
        mock_disk.total_space = 1000000
        mock_disk.used_space = 500000
        mock_info.return_value = mock_disk
        connected = await service.check_connection()
        assert connected is True


@pytest.mark.asyncio
async def test_yandex_list_files():
    service = YandexDiskService("test_token")
    mock_file = Mock()
    mock_file.name = "test.txt"
    mock_file.path = "/test.txt"
    mock_file.type = "file"
    mock_file.size = 1024
    with patch.object(service.client, "listdir") as mock_listdir:
        mock_listdir.return_value = [mock_file]
        files = await service.get_files_list("/")
        assert len(files) == 1
        assert files[0]["name"] == "test.txt"
