import contextlib
import sys
from pathlib import Path

import click
import pymupdf

from dowpi import __version__
from dowpi.converter import convert_pdf
from dowpi.images import relink_images


def _parse_pages(ctx, param, value):
    if value is None:
        return None
    pages: set[int] = set()
    try:
        for part in value.split(","):
            part = part.strip()
            if "-" in part:
                start_s, end_s = part.split("-", 1)
                start, end = int(start_s), int(end_s)
                if start < 1 or end < start:
                    raise ValueError
                pages.update(range(start, end + 1))
            else:
                number = int(part)
                if number < 1:
                    raise ValueError
                pages.add(number)
    except ValueError:
        raise click.BadParameter("formato non valido, esempio: '1-5,8'") from None
    return sorted(page - 1 for page in pages)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="dowpi")
@click.argument(
    "pdf_path",
    metavar="PDF",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="File Markdown di destinazione. [default: <PDF>.md]",
)
@click.option(
    "-p",
    "--pages",
    "pages_spec",
    metavar="SPEC",
    callback=_parse_pages,
    help="Pagine da convertire (1-based), es. '1-5,8'. [default: tutte]",
)
@click.option(
    "--images/--no-images",
    default=True,
    show_default=True,
    help="Estrai le immagini del PDF e referenziale nel Markdown.",
)
@click.option(
    "--image-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Cartella per le immagini estratte. [default: <output>_images]",
)
@click.option(
    "--image-format",
    type=click.Choice(["png", "jpg"]),
    default="png",
    show_default=True,
    help="Formato delle immagini estratte: jpg pesa molto meno sulle foto.",
)
@click.option(
    "--image-dpi",
    type=click.IntRange(36, 600),
    default=150,
    show_default=True,
    help="Risoluzione delle immagini estratte.",
)
@click.option(
    "--keep-headers",
    is_flag=True,
    help="Non rimuovere header/footer ripetuti e numeri di pagina.",
)
@click.option(
    "--ocr",
    is_flag=True,
    help="OCR sulle pagine senza testo selezionabile (PDF scansionati). Richiede Tesseract; "
    "le immagini delle pagine passate in OCR non vengono estratte.",
)
def main(
    pdf_path, output, pages_spec, images, image_dir, image_format, image_dpi, keep_headers, ocr
):
    """Converte PDF in Markdown ottimizzato per gli LLM."""
    output = output or pdf_path.with_suffix(".md")
    image_dir = image_dir or output.with_name(output.stem + "_images")

    # i messaggi di pymupdf e pymupdf4llm vanno su stderr: stdout resta solo per l'output
    pymupdf.set_messages(stream=sys.stderr)
    try:
        with contextlib.redirect_stdout(sys.stderr):
            markdown = convert_pdf(
                pdf_path,
                pages=pages_spec,
                write_images=images,
                image_dir=image_dir if images else None,
                image_format=image_format,
                image_dpi=image_dpi,
                strip_repeated=not keep_headers,
                ocr=ocr,
            )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if images:
        markdown = relink_images(markdown, image_dir, output.parent)
        if image_dir.is_dir() and not any(image_dir.iterdir()):
            image_dir.rmdir()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    click.echo(f"{output} scritto (~{len(markdown) // 4} token)", err=True)
    if not markdown and not ocr:
        click.echo("nessun testo estratto: se il PDF è scansionato, riprova con --ocr", err=True)
