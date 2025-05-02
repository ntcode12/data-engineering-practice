import os
import zipfile
import pytest
from pathlib import Path

import main

@pytest.mark.parametrize("uri, final_path, expected", [
    ("https://example.com/path/to/file.csv", "downloads", "downloads/file.csv"),
    ("http://host/name.zip?x=1", "/tmp", "/tmp/name.zip"),
    ("s3://bucket/key", "data", "data/key"),
])
def test_get_filename(uri, final_path, expected):
    result = main.get_filename(uri, final_path)
    assert result == expected

def create_zip(tmp_path, files):
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return str(zip_path)

def test_zip_to_csv_success(tmp_path):
    content = "col1,col2\n1,2"
    files = {"data.csv": content, "readme.txt": "info"}
    zip_path = create_zip(tmp_path, files)
    csv_path = main.zip_to_csv(zip_path)
    assert csv_path is not None
    csv_file = Path(csv_path)
    assert csv_file.exists()
    assert csv_file.read_text() == content
    # zip removed
    assert not os.path.exists(zip_path)

def test_zip_to_csv_no_csv(tmp_path, capsys):
    files = {"doc.txt": "hello"}
    zip_path = create_zip(tmp_path, files)
    result = main.zip_to_csv(zip_path)
    captured = capsys.readouterr()
    assert "No CSV found" in captured.out
    assert result is None
    # zip should remain
    assert os.path.exists(zip_path)

@pytest.mark.asyncio
async def test_download_file_success(tmp_path):
    # 1) Build a real zip on disk
    files = {"test.csv": "a,b\n3,4"}
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)

    # 2) Capture its bytes up-front
    original_bytes = zip_path.read_bytes()

    # 3) DummyResponse that replays those bytes
    class DummyResponse:
        status = 200
        reason = "OK"
        async def read(self):
            return original_bytes      # <-- uses the pre-truncated bytes
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass

    class DummySession:
        def get(self, url): return DummyResponse()

    # 4) Run the downloader
    csv_path = await main.download_file(DummySession(), "http://example.com/test.zip", str(tmp_path))

    # 5) Assert it worked
    assert csv_path is not None
    text = Path(csv_path).read_text()
    assert text == "a,b\n3,4"

@pytest.mark.asyncio
async def test_download_file_404(tmp_path, capsys):
    class DummyResponse:
        status = 404
        reason = "Not Found"
        async def read(self):
            return b""
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass

    class DummySession:
        def get(self, url):
            return DummyResponse()

    result = await main.download_file(DummySession(), "http://example.com/missing.zip", str(tmp_path))
    captured = capsys.readouterr()
    assert "Download failed: 404 Not Found" in captured.out
    assert result is None