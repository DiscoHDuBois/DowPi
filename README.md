<p align="center">
  <img src="images/logo.png" alt="DowPi — CLI tool for converting PDF to Markdown" width="380">
</p>

# DowPi

Converte PDF in Markdown ottimizzato per gli LLM: struttura semantica (heading, liste,
tabelle), rimozione del rumore (header/footer ripetuti, numeri di pagina, separatori) e
meno token possibile.

## Installazione

Richiede Python 3.10+.

```sh
git clone https://github.com/DiscoHDuBois/DowPi.git
cd DowPi
pip install .
```

## Uso

```sh
dowpi documento.pdf                  # crea documento.md
dowpi documento.pdf -o note.md       # percorso di output esplicito
dowpi documento.pdf -p 1-5,8         # converte solo alcune pagine
dowpi documento.pdf --no-images      # non estrarre le immagini
dowpi documento.pdf --keep-headers   # mantieni header/footer ripetuti
dowpi documento.pdf --image-format jpg --image-dpi 96   # immagini più leggere
```

Il Markdown va nel file di output; i messaggi (avanzamento, OCR) vanno su stderr.

### Immagini

Le immagini estratte finiscono in `<output>_images/` (o in `--image-dir`) come
`<pdf>-p<pagina>-<n>.<ext>` e sono referenziate con percorsi relativi al file Markdown.
Per risparmiare token e spazio:

- le immagini identiche vengono salvate e referenziate una volta sola;
- quelle presenti su quasi tutte le pagine (loghi, filigrane) vengono scartate, salvo
  con `--keep-headers`;
- icone e filetti più piccoli del 5% della pagina vengono scartati;
- rilanciando la conversione, le immagini della conversione precedente dello stesso PDF
  vengono sostituite (gli altri file della cartella non vengono toccati).

Il testo trovato dentro le immagini (etichette di schemi, OCR) è reso come citazione
preceduta da `> [image text]`.

## Roadmap

- `--diagrams llm` (opt-in): conversione dei diagrammi tramite LLM multimodale — Mermaid
  per gli schemi a blocchi, netlist/descrizione strutturata per gli schemi circuitali.

## Licenze

DowPi si appoggia a [PyMuPDF](https://pymupdf.readthedocs.io/) e pymupdf4llm (AGPL-3.0 o
licenza commerciale Artifex). pymupdf4llm installa anche `pymupdf-layout`, distribuito con
licenza Polyform Noncommercial o commerciale Artifex.
