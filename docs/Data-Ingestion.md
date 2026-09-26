# Data Ingestion

`ingest-corpus` is the pipeline's only ingestion command. It is available for
the operational profile and normalizes configured intake exports into
`workspaces/operational/data/ready/` JSONL packets.

Question answering does not retrieve those packets directly. It retrieves from
the operational QMD collections: `Base`, `Consulting`, and `Customers`.
`ingest-corpus` remains useful for preparing operational artifacts and recording
their source manifest, but it is not a schema graph exporter.

There is no `ingest-substrate` command, schema graph input, or `substrate-cli`
dependency.
