import io
import zipfile

import pytest

from jnu_mvp.pack import make_zip


def test_make_zip_requires_index(tmp_path):
    (tmp_path / "style.css").write_text("body{}")
    with pytest.raises(FileNotFoundError):
        make_zip(tmp_path)


def test_make_zip_excludes_secrets_and_junk(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / ".env").write_text("SECRET=1")
    (tmp_path / "jnu-mvp.json").write_text("{}")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("x")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")

    names = zipfile.ZipFile(io.BytesIO(make_zip(tmp_path))).namelist()
    assert "index.html" in names
    assert "assets/app.js" in names
    assert ".env" not in names
    assert "jnu-mvp.json" not in names
    assert not any(n.startswith("node_modules") for n in names)
