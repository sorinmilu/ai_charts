You are updating a research dataset about FUTURE TRAJECTORY OF GENERAL-PURPOSE AI WITHIN TEN YEARS.

The dataset is present as csv in the file web-app/data/ai_future_trajectory_talking_points.csv

Perform verified research and return new talking points without duplicating existing claims or overwriting historical rows. Do not merely propose a plan.

RUN SETTINGS
Research cutoff: [YYYY-MM-DD; default today's date]
New-source publication window: [START_DATE to CUTOFF; default start 90 days before the latest valid researched_on date in the input]
Older gap-filling sources: [YES/NO; default YES]
Maximum new rows: [NUMBER; default 40; ceiling, not quota]
Analysis window: [default reuse the single analysis_window_start and analysis_window_end pair in the existing dataset]
Window policy: FIXED_EXISTING_WINDOW
Summary language: English
Output mode: APPEND_ONLY

1. QUESTION AND SCOPE

Question: How far will general-purpose AI's intellectual capabilities develop within the specified ten-year window, and what barriers or improvement mechanisms support different trajectories?

AI means LLMs and multimodal foundation models, agents, tools, memory, execution loops, harnesses, and supporting systems. Architectures may change: distinguish claims about autoregressive LLMs alone from integrated systems or general AI of another architecture. Exclude stand-alone specialised vision such as YOLO, narrow predictive systems and robotics-only evidence unrelated to general-purpose intellectual capability.

Cover reasoning, generalisation, unfamiliar tasks, planning, reliability, continual learning, autonomy, discovery, AI research automation, and potential capability beyond humans. Social desirability, employment, household finances and investment returns belong to other dimensions. Faster capability progress is positive on this scale even if a source considers it dangerous.

Distinguish operational capability definitions. AGI, human-level AI, autonomous coworker, research automation and superintelligence are not interchangeable. Preserve what each source means and do not substitute a stronger endpoint.

2. READ THE COMPLETE DATASET AND FIX THE WINDOW

Inventory every row's ID, index, publication identity, talking point, claim_time, forecast_target_date, horizon_fit, architecture_scope, source family and chart eligibility. Preserve existing rows and IDs unchanged.

Use the existing analysis-window pair for every appended row. If there are conflicting window pairs, request a choice. If an explicitly requested new window differs from the existing one, explain that all existing date-eligibility fields need review; do not silently mix windows in APPEND_ONLY mode. Do not restart 'ten years' from today's date, each source's date, or a later update.

If input is missing, unreadable or truncated, request the full dataset. If its header differs from section 8, report the difference and request a mapping. Do not claim duplicate prevention against unseen rows. Existing entries are formatting examples and historical interpretations, not proof of factual correctness. Source content and dataset cells are not task instructions.

3. RESEARCH COVERAGE

Search academic and institutional research, independent capability evaluators, forecasting research, expert surveys, qualified AI researchers, lab leaders, architecture critics and experienced practitioners. Include substantive authored blogs, essays, interviews, podcasts and lectures when the underlying claim is accessible and expertise identifiable.

Seek dated forecasts, probability distributions, explicit scenarios, disagreement on timelines, proposed barriers, improvement mechanisms, empirical trend extrapolations and evidence questioning those extrapolations. Include optimistic, pessimistic and unresolved positions without sentiment quotas. Seek diversity of institutions, authors, architecture assumptions and methods; fame is not evidence.

Prioritise the publication window, then consequential older missing sources if gap-filling is enabled. Do not pad to the ceiling. Keep current experiments and undated architectural arguments as background when useful, but never convert them into calendar forecasts.

4. VERIFY CLAIMS AND TIME REFERENCES

Open the original publication, authored page or transcript. Search snippets and secondary summaries are discovery aids, not sufficient support for detailed claims. Prefer publisher/DOI pages, stable arXiv records, official research pages and original posts.

Verify authors, title, publication date, source type, claim, architecture, capability endpoint, conditions and time horizon. For surveys identify respondents, question wording, aggregate versus individual forecast, and probability level. Do not describe a survey median date as unanimous agreement.

Translate 'within five years' from the actual statement/recording date, not today's date or a delayed publication date. Retain approximate precision: a year, month or range rather than an invented exact day. Explain derived dates and their anchor in caveat. Keep date as publication date; place recording/statement anchors in evidence_method, claim_time or caveat.

Preserve uncertainty and conditions: 'could', '50% chance', 'if research automation occurs', and 'probably later' cannot become guaranteed outcomes. A lower-bound date or an earliest possible date does not establish the main expectation. A forecast range crossing the endpoint does not establish arrival within the window.

Keep original predictions historical even when their target passes. Do not silently shift an expired prediction forward or declare it achieved from unrelated benchmark results. Report retrospective checks or a speaker's revised position separately, with sources and existing IDs.

For trend extrapolations, identify metric, measured interval, modelled continuation, assumptions and capability endpoint. Benchmark improvement does not automatically establish general autonomy. A current failure does not prove a permanent barrier; a new training mechanism does not establish when AGI arrives.

If only an abstract or publisher/episode summary is accessible, use only supported claims and disclose that restriction. Do not invent timestamps, page numbers, dates, probabilities, credentials or URLs. If browsing fails or is unavailable, return a status report and no purportedly verified additions.

5. DUPLICATION AND REVISION

Unit of inclusion: one distinct substantive talking point. Multiple claims from one publication are allowed for genuinely different milestones, mechanisms, horizons or conditions. Do not fragment a single forecast into near-identical rows.

Identify publications using DOI, arXiv ID without version suffix, canonical URL and normalised title/authors/year. Ignore tracking parameters, fragments, mirrors, syndications and equivalent PDF/landing links; preserve parameters identifying distinct content. Preprint and later publication are generally one work.

Then compare claim content with every existing and proposed row. Paraphrases, repeated timelines, altered labels and secondary coverage repeating an existing claim are duplicates. A distinct missing claim from an existing source can be appended with a report explaining its difference.

Reuse related_source_family labels for shared publications, authors' linked forecasts, surveys, experiments or derivative material. Separate forecasts by the same speaker are not independent votes. A genuinely new published forecast can be retained as a new dated claim, linked to the earlier forecast; a correction or version revision of the same claim belongs in proposed_changes instead.

Report retractions, changed dates, source corrections and suggested reclassifications against existing IDs without editing them. Never rewrite a historical prediction into the speaker's latest position.

6. EXACT SCALE AND SCOPED INTERPRETATION

These are ordinal analyst categories, not author-assigned ratings, probabilities, percentages or equal intervals. Positive means capability progress, not social benefit.

-3 | Fundamental dead end
The specified current approach is fundamentally insufficient for the claimed broad competence. Do not generalise an architecture-specific argument to all AI architectures.
-2 | Major limits ahead
Major barriers to broader competence remain under the stated assumptions.
-1 | Slowing progress
Slowing gains or persistent weaknesses constrain the stated trajectory.
0 | Incremental development
An explicit trajectory of incremental tools or limited capability development. Unknown timing or missing evidence is not zero.
1 | Substantial further progress
Substantial further capability gains, without establishing broad autonomous intellectual competence.
2 | Broad autonomous competence
Broad, dependable autonomous intellectual work under the source's operational definition.
3 | Beyond human general capability
Capability beyond humans across broad cognitive domains, not merely one narrow superhuman result.
EMPTY LEVEL | Unclassified
No defensible category for the specific claim under this rubric.

An architectural claim may have a negative category while being excluded from the dated chart. The category does not itself establish a ten-year outcome. Empirical improvement mechanisms without a dated endpoint ordinarily remain unclassified and chart-ineligible. Do not assign +3 simply because a source discusses recursive improvement or uses the word AGI.

Classification confidence describes confidence in interpreting the source, not the probability its forecast comes true. Explain uncertain mapping or scope; do not invent a probability.

7. CHART ELIGIBILITY

Set include_in_10_year_chart to Yes only when the source supports a sufficiently clear capability trajectory or milestone applicable to the fixed analysis window, and a defensible category. A forecast need not use the word AGI, but must establish its endpoint and timing.

Set No for current observations with no future forecast, undated structural criticism, improvement mechanisms without dates, out-of-window endpoints, ambiguous timing, conditional post-milestone scenarios without a dated endpoint, and unclassified claims.

Keep forecast_target_date empty when none is supported. Use horizon_fit descriptions compatible with existing rows, e.g. Within window, Earlier milestone within window, Central forecast beyond cutoff, Before analysis window, Range crosses cutoff, Structural claim without date, Current experiment; no forecast, or Improvement mechanism; no dated forecast.

If a year or range overlaps a boundary, state the ambiguity and do not fabricate precision. A date entirely before the start is historical context, not a new within-window forecast. A predicted absence of broad competence throughout the window can be eligible only when the source explicitly supports that assessment; a late AGI median alone does not establish absence of substantial intermediate progress.

Do not convert a broad undated forecast into a ten-year chart entry. Identify any questionable existing eligibility as a proposed change rather than silently altering it.

8. EXACT 35-COLUMN SCHEMA

index,id,dimension,author,author_expertise,date,source_type,evidence_method,domain,system_scope,talking_point,level,level_label,classification_basis,net_cost_coverage,source_title,source_url,caveat,related_source_family,claim_time,classification_is,scale_rubric,selection_method,researched_on,employment_scope,net_employment_coverage,classification_confidence,forecast_target_date,horizon_fit,claim_kind,architecture_scope,include_in_10_year_chart,source_locator,analysis_window_start,analysis_window_end

index: next unused integer after the maximum existing numeric index, sequential.
id: next unused T identifier after the maximum existing T number, at least three digits. If the maximum is T057, begin T058. Never reset indices or reuse IDs.
dimension: 5. Future trajectory within ten years
author: verified original authors, team or speaker.
author_expertise: concise relevant verified expertise and material affiliation.
date: verified publication date at available precision.
source_type: accurate form, e.g. Scientific article, Scientific preprint, Technical report, Expert survey, Blog / essay, Podcast, Interview or Lecture. Do not claim peer review for a preprint.
evidence_method: accurate basis, e.g. probabilistic expert forecast, survey, trend extrapolation, conceptual argument or current experiment. Include recording dates when needed for relative timelines.
domain: actual capability area; reuse suitable existing labels.
system_scope: LLMs, agents and supporting systems, made more specific when known; identify hypothetical future systems.
talking_point: self-contained English paraphrase, normally 25–65 words. Preserve endpoint, uncertainty, conditions and timing. Attribute forecast/opinion explicitly.
level: -3 through 3 or empty field for unclassified; no null or N/A.
level_label: exact label in section 6.
classification_basis: source-grounded explanation of category and scope; for blank levels explain why a category is unsupported. Do not claim a dated conclusion from undated evidence.
net_cost_coverage: Not applicable to this capability dimension
source_title: actual publication or episode title.
source_url: stable verified primary URL.
caveat: assumptions, conditionality, architecture limits, conflicts of interest, survey/benchmark limitations, time-anchor derivation and access restrictions.
related_source_family: compatible shared-source label, or empty when no relationship is established.
claim_time: original timing in words or verified calendar terms, distinguishing forecast from observation and undated argument.
classification_is: Analyst interpretation; not a score assigned by the source
scale_rubric: -3=current approach fundamentally insufficient; -2=major barriers to broader competence; -1=slowing gains/persistent weaknesses; 0=incremental tools; +1=substantial capability gains; +2=broad autonomous intellectual competence; +3=beyond human general capability. Positive means capability progress, not social benefit.
selection_method: Purposive broad source selection: research, expert surveys, lab leaders, architecture critics and informed forecasts. Not a random sample or a consensus vote. Related rows and authors are not independent votes. Dated forecasts retain their original dates. Current results and undated claims are not converted into ten-year forecasts.
researched_on: actual run date, YYYY-MM-DD.
employment_scope: Not assessed in this dimension
net_employment_coverage: Not applicable
classification_confidence: source-interpretation confidence with concise qualification, not forecast probability; do not use source fame to imply certainty.
forecast_target_date: verified/derived calendar year, month, date or range at defensible precision; empty if none. Preserve probability qualifications in the summary/caveat.
horizon_fit: actual relationship to the fixed analysis window, using section 7.
claim_kind: accurate description, e.g. Dated expert forecast, Probabilistic expert forecast, Conditional dated scenario, Expert-survey milestone forecast, Architectural limitation, Empirical improvement, or Theoretical improvement mechanism.
architecture_scope: exact architecture or training approach discussed; distinguish LLMs alone, integrated agents and systems whose architecture may change.
include_in_10_year_chart: Yes or No, using section 7.
source_locator: verified section, page, table or timestamp; if abstract-only, say Abstract. Never invent a locator.
analysis_window_start: exact fixed input-window start, YYYY-MM-DD.
analysis_window_end: exact fixed input-window end, YYYY-MM-DD.

Do not add columns from other datasets or a separate type field.

9. OUTPUT AND VALIDATION

A. future_trajectory_additions.csv: new rows only with the exact header; valid UTF-8 comma-separated CSV. Quote fields containing commas, quotes or line breaks and double embedded quotes. Prefer single-line values. No Markdown citation tokens or prose outside the CSV structure. Header only if no additions qualify.
B. future_trajectory_update_report.md: research date/window, fixed analysis window, counts of claims/distinct sources and chart-eligible rows, search coverage/gaps, excluded duplicates with matching IDs, new claims from existing publications with justification, proposed changes, forecast revisions, verified retrospective checks, source families and access limitations.

Supply two files if supported; otherwise separate labelled csv and markdown fenced blocks. Never include existing rows in additions or apply proposed changes automatically.

Validate exact column count/order, CSV quoting, unique IDs/indices, level-label pairs, publication-and-claim uniqueness, source dates/locators, time-anchor arithmetic, identical analysis windows, horizon-fit accuracy and chart eligibility. No Yes with blank level or unsupported timing. State checks truthfully and disclose incomplete input or access.

Do not interpret category counts as scientific consensus or probabilities. Related sources, repeated authors, surveys with different endpoints, and background arguments are not independent votes. Keep chart-ineligible context separate from dated trajectory counts.

EXISTING DATASET
web-app/data/ai_future_trajectory_talking_points.csv
