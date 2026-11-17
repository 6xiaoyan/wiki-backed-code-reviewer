# PyGoat material token inventory

Counts are sums of independently tokenized UTF-8 file contents. Both encodings are proxies; actual baseline-model tokenizers may differ.

| Category | Files | o200k_base | cl100k_base |
| --- | ---: | ---: | ---: |
| judge_ground_truth | 1 | 23,424 | 23,435 |
| judge_scoring_code_and_config | 9 | 14,161 | 14,068 |
| judge_supporting_materials | 22 | 79,028 | 78,811 |
| rules_core | 4 | 13,650 | 14,918 |
| rules_optional-style | 2 | 42,132 | 42,025 |
| rules_supplemental | 5 | 27,575 | 27,406 |
| target_documentation | 11 | 14,827 | 14,857 |
| target_other_text | 38 | 20,866 | 20,758 |
| target_python | 80 | 32,138 | 31,554 |
| target_static_assets | 21 | 61,958 | 61,758 |
| target_templates | 117 | 80,212 | 79,227 |

## Combined input sizes

| Scope | o200k_base | cl100k_base |
| --- | ---: | ---: |
| python_and_templates | 112,350 | 110,781 |
| python_templates_and_core_security_rules | 126,000 | 125,699 |
| python_templates_and_all_security_rules | 153,575 | 153,105 |
| all_target_text | 210,001 | 208,154 |
| all_rule_documents | 83,357 | 84,349 |

## Boundaries

- Judge files and ground truth are not model inputs.
- Target text includes Solutions/solution.md and teaching/discussion content inside templates. These are preserved upstream materials, not an approved answer-free experiment input.
- Static assets include SVG and CSS; they must not be presented as Python backend code size.
- Optional style documents are excluded from security-only rule totals.
- Raw security documents require a version/applicability review before group B is frozen.
- No target code, dependencies, model calls or vulnerability evaluation were executed.
- No chat framing, system prompts, tool schemas, image tokens, reasoning or output budget is included.
