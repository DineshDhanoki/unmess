# Live synthetic demo

The web demo runs the repository's real PyMuPDF parser, structure-aware chunker, citation resolver, and source-region renderer on three bundled fictional invoices. Visitors choose a sample and press **Run the real pipeline**; the result is computed then, rather than loaded from a saved answer. The public page has no upload control.

## Run locally

From the repository root with Python 3.11 or 3.12 and [uv](https://docs.astral.sh/uv/) installed:

```bash
uv sync --extra ui --dev --locked
uv run --extra ui streamlit run ui/live_demo.py
```

Open the local URL printed by Streamlit. Try invoices 00 and 01: they should return different sellers, totals, and chunk IDs. The highlighted page uses the current chunk's source region, which may cover more than the exact total line.

## Publish on Streamlit Community Cloud

1. Connect the GitHub repository to [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).
2. Select `DineshDhanoki/unmess`, the `main` branch, and `ui/live_demo.py` as the entrypoint.
3. Set Python to **3.12** in advanced settings. The app-specific `ui/requirements.txt` installs this repository with its UI extra and pins Streamlit.
4. Deploy, then run all three invoices in the public app and check the source image. Add the verified URL to the repository website field and the README.

The hosting server processes only the bundled synthetic documents. Do not add a file uploader or imply that hosted processing is private local processing. The CLI remains the path for a user's own documents. Search, an API, and the full review UI remain roadmap work.
