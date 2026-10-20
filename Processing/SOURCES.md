# Source contracts

Inspected 2026-10-20. Source revisions are pinned, not floating `main`.

## OpsAgent

- [Paper v1, data processor §III-B](https://arxiv.org/html/2510.24145v1#S3.SS2)
- [Public data processor](https://github.com/Johnn13/OpsAgent/blob/6d61b8bb9c6bc9de6347601562c644fade324765/utils/data_processer.py)
- [Published CNN weights](https://github.com/Johnn13/OpsAgent/blob/6d61b8bb9c6bc9de6347601562c644fade324765/patterncla.pt)

Commit: `6d61b8bb9c6bc9de6347601562c644fade324765`.
Checkpoint SHA-256:
`71e257758e2becbe611fc489203407dce0ff114ea703d87ee7aca3eba1040753`.

Implemented profile follows the public code: mean/sample std over the supplied
series, threshold >3, 30-point CNN input (20 before/10 after with boundary
adjustment), top24 shape groups ranked by maximum deviation, suppress >10 peaks
when maximum deviation <6. Top5 pods/metrics are summary annotations, not
hard filters in that code. Paper v1 describes sliding statistics and top5
selection, so this is deliberately named a code-based adaptation.

Logs use keyword filtering, binary TF–IDF without normalization, English stop
words, mean score across vocabulary, 80th-percentile threshold, and global
minute/template deduplication. Drain3 0.9.11's actual `template_mined` output
replaces the source's nonexistent `log_template` lookup/fallback. Raw messages
and IDs are retained as provenance, not additional selected evidence.

Trace q=.98 follows code, whereas paper v1 says .95. RCABench call type is
service + operation + span kind. Use exact (trace_id, span_id) identities,
unknown rather than invented self-call when parent missing, ns→ms conversion,
and correct 60s bucket endpoints. Preserve top24 windows and top24 recurrent
(count≥2) three-hop paths.

No upstream source files are vendored. Shape architecture is a checkpoint
compatibility adapter; the original checkpoint is downloaded separately.

## FoundRoot

- [Camera-ready paper, §3.3–3.4](https://netman.aiops.org/wp-content/uploads/2026/01/foundroot_camera_ready.pdf)
- [Public preprocessing script](https://github.com/NetManAIOps/FoundRoot/blob/5a64aeef63ae84893c644081204b4f9d02e947ae/utils/preprocess_dejavu.py)

Commit: `5a64aeef63ae84893c644081204b4f9d02e947ae`.

The script explicitly describes reverse engineering of DejaVu release artifacts
and marks k=4, minimum reference points=3 and several selection rules speculative.
The paper establishes k-sigma filtering and textual metric input, not exact
RCABench preprocessing parameters.

Implemented: paired normal/abnormal windows, sample std, bidirectional k-sigma,
all dimensions retained and full selected series stored. No GT-assisted root
retention, failed-injection exclusion, 50-metric cap, shuffling, zero padding or
DejaVu-specific temporal grid. Zero-variance baselines remain insufficient.
The evidence detector does not accept annotations as an argument.

FoundRoot is metric-only here. Logs/traces are not attributed to its method.
Path association is a separate, privileged evaluation stage in this project.

## Interpretation

Input adaptation differences are explicit in each generated profile. These runs
test evidence extraction on our RCABench release; they do not reproduce either
paper's reported dataset-level RCA accuracy. No assumption of complete evidence
recall or causal identification is made.
