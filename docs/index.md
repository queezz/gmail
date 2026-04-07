# gmail-parser

**gmail-parser** is a small Python toolkit for turning a local Gmail (or other) **`.mbox`** export into a **CSV** of messages enriched with **English summaries**, **action hints**, and **tags**—using the **OpenAI API** for the text understanding step.

You run one CLI command; the rest is file I/O, optional caching, and progress on the terminal.

## At a glance

| Step | What happens |
|------|----------------|
| Load | Read the mbox, decode multipart bodies, optionally strip HTML, cap body length. |
| Filter | CLI flags can limit how many messages you pull and cut off by date. |
| Process | Each message is sent (or served from cache) through the model; results are merged into a table. |
| Output | A CSV under `data/` with the original fields plus summary-style columns. |

Paths and defaults (mbox location, output files, model name, cache versioning) live in **`gmail_parser.config`** so you can change them in one place if your layout differs.

## Try it

Install the package (from the repo root), set your API key, then run:

```bash
pip install -e .
export OPENAI_API_KEY=your_key   # Windows PowerShell: $env:OPENAI_API_KEY = "your_key"
gmail-parser --since 2024-01-01 --limit 50
```

Use **`--help`** on the CLI for options. For generated Python API docs, see **API** in the sidebar.
