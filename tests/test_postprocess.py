from dowpi.postprocess import clean


def test_clean_removes_omitted_picture_placeholders():
    pages = [
        "## Titolo\n\n**==> picture [300 x 225] <==**\n\ntesto\n",
        "**==> picture [612.0 x 79.5] <==**\n\n",
    ]
    assert clean(pages) == "## Titolo\n\ntesto\n"


def test_clean_keeps_text_mentioning_pictures():
    page = "picture [1] omessa nel testo originale.\n"
    assert clean([page]) == page


_START = "**----- Start of picture text -----**<br>\n"
_END = "**----- = End of picture text = -----**<br>\n"


def test_picture_text_becomes_labelled_blockquote():
    page = f"testo\n\n{_START}Client API<br>Database<br>{_END}\n\n"
    assert clean([page]) == "testo\n\n> [image text]\n> Client API\n> Database\n"


def test_picture_text_table_fallback_is_quoted():
    page = f"{_START}|||\n|---|---|\n|a|b|\n\n{_END}\n\n"
    assert clean([page]) == "> [image text]\n> |||\n> |---|---|\n> |a|b|\n"


def test_empty_picture_text_is_removed():
    assert clean([f"testo\n\n{_START}<br>{_END}"]) == "testo\n"


def test_repeated_picture_text_is_not_page_furniture():
    pages = [f"## Pagina {i}\n\n{_START}Gateway<br>Cache v{i}<br>{_END}" for i in range(4)]
    result = clean(pages)
    assert result.count("> Gateway") == 4
    assert "> Cache v3" in result


def test_protected_last_line_does_not_expose_body_text_as_footer():
    pages = [f"## P{i}\n\nstessa frase\n\n{_START}Gateway<br>{_END}" for i in range(4)]
    assert clean(pages).count("stessa frase") == 4
