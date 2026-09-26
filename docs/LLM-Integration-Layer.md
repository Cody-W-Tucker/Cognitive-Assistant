# LLM Integration Layer

`lib.llm` creates configured provider clients and exposes synchronous and
asynchronous text generation helpers. Question answering uses the configured
direct client only after QMD returns current, non-empty retrieval evidence.

QMD is a local CLI retrieval dependency. It returns JSON result records that
are bounded and cited in the synthesis prompt; final answers do not expose
those citations.
