# LLM review evidence for the final report

[llm-review-example.json](llm-review-example.json) preserves the input/output
example supplied in Section 6.1 of the shared final report as exported on
13 October 2026. It concerns May Mobility's **Senior Accountant** posting,
`greenhouse|may mobility|id:8746085002`.

The report presents it as an incorrect AV-relevance decision: the output sets
`av_relevant` to `true` with High confidence by linking accounting to vehicle
production. This is a reported review example, not a new evaluation run, a raw
provider trace or an approved replacement classification.

The JSON was parsed and reformatted, with its values checked against the report
export. Original ellipses and apostrophes are preserved; omitted text in the
report example has not been reconstructed. This file does not modify production
datasets or the published database.

The team should separately document the actual prompt change and recheck result.
No corrected rerun or measured improvement is established by this example alone.
The concise report can link here instead of reproducing the full JSON.
