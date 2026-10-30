"""Public, synthetic-only walkthrough of Unmess's real Python parsing path."""

from __future__ import annotations

import streamlit as st

from unmess.demo import InvoiceDemoResult, run_invoice_demo

REPOSITORY = "https://github.com/DineshDhanoki/unmess"
SAMPLE_LABELS = {
    "00": "Invoice 00 · one-page fictional invoice",
    "01": "Invoice 01 · a different fictional total",
    "02": "Invoice 02 · another fictional seller and total",
}

st.set_page_config(
    page_title="Unmess | Live evidence demo",
    page_icon="📄",
    layout="wide",
)
st.markdown(
    "<style>[data-testid='stMainBlockContainer'] {max-width: 1180px;}</style>",
    unsafe_allow_html=True,
)

st.caption("UNMESS  /  LIVE SYNTHETIC DEMO")
st.title("A number is not the whole answer.")
st.markdown(
    "An invoice total can look convincing. **Unmess shows where it came from.** "
    "Choose a fictional invoice and run the repository's real PyMuPDF parser, "
    "chunker, and source-highlighting code."
)

with st.container(border=True):
    st.subheader("Try it yourself")
    selected = st.selectbox(
        "Choose a bundled fictional invoice",
        options=list(SAMPLE_LABELS),
        format_func=lambda code: SAMPLE_LABELS[code],
        help="Only these three synthetic documents can be processed here.",
    )
    run_requested = st.button("Run the real pipeline", type="primary")
    st.caption(
        "This public demo processes only bundled synthetic PDFs on the hosting server. "
        "There is no upload control, account, model download, or external document service."
    )

if run_requested:
    with st.spinner("Parsing the fictional invoice and resolving its source region..."):
        st.session_state["demo_result"] = run_invoice_demo(selected, highlight=True)
        st.session_state["demo_code"] = selected

result: InvoiceDemoResult | None = st.session_state.get("demo_result")
if result is None or st.session_state.get("demo_code") != selected:
    st.info("Pick an invoice and press **Run the real pipeline** to see a fresh result.")
else:
    st.success("Parsed from the selected synthetic PDF. The answer below is produced at run time.")
    summary, source = st.columns([0.9, 1.1], gap="large")
    with summary:
        st.subheader("What Unmess found")
        st.metric("Invoice total", result.total.removeprefix("Total INR: "))
        st.write(result.seller)
        st.write(f"**Parser:** {result.parser_name}")
        st.write(f"**Source page:** {result.page_number}")
        st.write("**Citable chunk ID**")
        st.code(result.chunk_id, language=None)
        st.caption("A chunk is a piece of extracted content linked back to its source region.")
        st.download_button(
            "Download this fictional source PDF",
            data=result.pdf.read_bytes(),
            file_name=result.pdf.name,
            mime="application/pdf",
        )
        st.caption(
            "The total is read from the PDF's parsed text. Switching invoices changes "
            "the answer and citation."
        )
    with source:
        st.subheader("Where it came from")
        if result.highlighted_page is not None:
            st.image(
                result.highlighted_page,
                caption="Highlighted source chunk on the synthetic invoice page.",
                width="stretch",
            )
        st.caption(
            "The highlighted area is the cited chunk, which is broader than the exact "
            "total line. Precise answer-line highlighting is future work."
        )

st.divider()
st.subheader("What this proves—and what comes next")
st.write(
    "Today: local PDF extraction, structure-aware chunks, page/region provenance, "
    "and a visible source preview. Search, an API, and a full review UI are still planned."
)
st.write(
    "The public demo accepts no personal documents. To process your own files, "
    "run Unmess locally and follow the repository's data-safety guidance."
)
code_link, issue_link = st.columns(2)
with code_link:
    st.link_button("Explore the source code ↗", REPOSITORY)
with issue_link:
    st.link_button(
        "Find a good first issue ↗",
        f"{REPOSITORY}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22",
    )
