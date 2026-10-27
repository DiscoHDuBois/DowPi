import pymupdf

from dowpi.images import (
    dedupe_images,
    drop_small_images,
    image_stem,
    publish_images,
    relink_images,
)
from dowpi.postprocess import remove_repeated_furniture


def _write(directory, name, content):
    path = directory / name
    path.write_bytes(content)
    return str(path.resolve())


def _png(directory, name, width, height):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
    path = directory / name
    pix.save(str(path))
    return str(path.resolve())


def test_dedupe_merges_identical_images(tmp_path):
    a = _write(tmp_path, "a.png", b"figura")
    b = _write(tmp_path, "b.png", b"figura")
    pages = [f"testo\n\n![]({a})", f"altro\n\n![]({b})"]

    assert dedupe_images(pages, tmp_path) == [f"testo\n\n![]({a})", "altro\n\n"]


def test_dedupe_drops_images_repeated_on_most_pages(tmp_path):
    logos = [_write(tmp_path, f"logo{i}.png", b"logo") for i in range(4)]
    figure = _write(tmp_path, "fig.png", b"figura")
    pages = [f"![]({logo})\n\npagina {i}" for i, logo in enumerate(logos)]
    pages[1] += f"\n\n![grafico]({figure})"

    result = dedupe_images(pages, tmp_path)

    assert all("logo" not in page for page in result)
    assert f"![grafico]({figure})" in result[1]


def test_dedupe_keeps_repeated_images_when_disabled(tmp_path):
    logos = [_write(tmp_path, f"logo{i}.png", b"logo") for i in range(4)]
    pages = [f"![]({logo})" for logo in logos]

    result = dedupe_images(pages, tmp_path, drop_repeated=False)

    assert result == [f"![]({logos[0]})", "", "", ""]


def test_dedupe_ignores_external_links(tmp_path):
    pages = ["![](https://example.com/x.png)"]
    assert dedupe_images(pages, tmp_path) == pages


def test_drop_small_images(tmp_path):
    # pagina A4 (595x842 pt) a 72 dpi
    icon = _png(tmp_path, "icon.png", 20, 20)
    rule = _png(tmp_path, "rule.png", 400, 3)
    figure = _png(tmp_path, "fig.png", 300, 200)
    page = f"![]({icon})\n![]({rule})\n![]({figure})"

    result = drop_small_images([page], tmp_path, [pymupdf.paper_rect("a4")], dpi=72)

    assert result == [f"\n\n![]({figure})"]


def test_publish_moves_renames_and_removes_previous_run(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    image_dir = tmp_path / "imgs"
    image_dir.mkdir()
    (image_dir / "doc-p9-1.png").write_bytes(b"vecchia")
    (image_dir / "altro-p1-1.png").write_bytes(b"di un altro PDF")
    (image_dir / "foto.jpg").write_bytes(b"dell'utente")
    a = _write(staging, "x-0002-00.png", b"a")
    b = _write(staging, "x-0002-03.png", b"b")
    c = _write(staging, "x-0005-01.png", b"c")

    result = publish_images(
        [f"![]({a}) ![]({b})", f"![]({c})"],
        staging,
        image_dir,
        stem="doc",
        page_numbers=[2, 5],
    )

    assert result == [
        f"![]({image_dir}/doc-p2-1.png) ![]({image_dir}/doc-p2-2.png)",
        f"![]({image_dir}/doc-p5-1.png)",
    ]
    assert sorted(p.name for p in image_dir.iterdir()) == [
        "altro-p1-1.png",
        "doc-p2-1.png",
        "doc-p2-2.png",
        "doc-p5-1.png",
        "foto.jpg",
    ]
    assert not any(staging.iterdir())


def test_image_stem_is_link_safe():
    assert image_stem("cartella/my report (v2).pdf") == "my_report_v2_"


def test_relink_makes_paths_relative_to_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    image_dir = tmp_path / "assets" / "imgs"
    image_dir.mkdir(parents=True)
    _write(image_dir, "p1.png", b"x")
    markdown = f"![a]({image_dir}/p1.png) e ![b](assets/imgs/p1.png)"

    result = relink_images(markdown, "assets/imgs", tmp_path / "out")

    assert result == "![a](../assets/imgs/p1.png) e ![b](../assets/imgs/p1.png)"


def test_image_lines_are_not_page_furniture():
    pages = [f"Titolo {i}\n\ntesto\n\n![](img/doc-{i}-1.png)" for i in range(4)]
    result = remove_repeated_furniture(pages)
    assert all("![](img/" in page for page in result)
