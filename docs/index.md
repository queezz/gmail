# gmail-parser

Parse a local `.mbox`, summarize messages with OpenAI (English summary, actions, keywords), and write `data/emails.csv`.

```bash
pip install -e .
set OPENAI_API_KEY=your_key
gmail-parser --since 2024-01-01 --limit 50
```

Default mbox path: `~/Dropbox/email_dump/mail.mbox` (see `gmail_parser.config`).
