# Structural Oracle Streamlit Launch

Run the two applications separately. Each has a fixed annotator identity and cannot select or write to the other annotator's response directory.

```bash
streamlit run scripts/streamlit_structural_oracle_annotator_a.py --server.port 8501
streamlit run scripts/streamlit_structural_oracle_annotator_b.py --server.port 8502
```

Annotator A writes only to `outputs/pferi_v2/measurement_feasibility_pilot/structural_oracle_responses/annotator_a/structural_oracle_responses.csv`. Annotator B writes only to the corresponding `annotator_b/` path. Neither application reads the restricted linkage CSV.

Before any real annotation is accepted, a non-annotator must inspect the rendered page, address bar, developer-visible network fields, downloaded CSV, displayed filenames, and both output directories for leakage or cross-annotator access.
