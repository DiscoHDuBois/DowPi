import os
import subprocess
import sys
from pathlib import Path

import pymupdf

import dowpi

_SRC = str(Path(dowpi.__file__).parents[1])


def _make_pdf(path):
    doc = pymupdf.open()
    for n, title in enumerate(["Uno", "Due", "Tre"]):
        page = doc.new_page()
        page.insert_text((72, 80), title, fontsize=20)
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 600, 400), False)
        pix.clear_with(60 + 50 * n)
        page.insert_image(pymupdf.Rect(72, 140, 522, 440), stream=pix.tobytes("png"))
    doc.save(str(path))


def _run(*args, cwd):
    env = {**os.environ, "PYTHONPATH": _SRC}
    return subprocess.run(
        [sys.executable, "-m", "dowpi", *args], cwd=cwd, env=env, capture_output=True, text=True
    )


def test_stdout_stays_clean(tmp_path):
    _make_pdf(tmp_path / "doc.pdf")
    result = _run("doc.pdf", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "doc.md scritto" in result.stderr


def test_image_format_jpg(tmp_path):
    _make_pdf(tmp_path / "doc.pdf")
    result = _run("doc.pdf", "--image-format", "jpg", "--image-dpi", "72", cwd=tmp_path)
    assert result.returncode == 0, result.stderr

    images = sorted(p.name for p in (tmp_path / "doc_images").iterdir())
    assert images == ["doc-p1-1.jpg", "doc-p2-1.jpg", "doc-p3-1.jpg"]
    assert pymupdf.Pixmap(str(tmp_path / "doc_images" / images[0])).width == 450
    assert "![](doc_images/doc-p1-1.jpg)" in (tmp_path / "doc.md").read_text()
