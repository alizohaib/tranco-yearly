# Tranco Unique Domains Archiver

This repository automates the collection of [**Tranco**](https://tranco-list.eu/) "Top‑1 M" domain lists and keeps a continually‑updated file of **unique domains for the current calendar year**.

* **`download-tranco-1m-for-year.py`** — multi‑threaded Python script that downloads each daily list in parallel, deduplicates them in‑memory, and writes a single sorted text file (one domain per line).
* **GitHub Actions workflow** — runs every day updates the year‑to‑date file, and commits it back to the repo; a *keep‑alive* step prevents the workflow from being auto‑disabled after 60 days of inactivity.

