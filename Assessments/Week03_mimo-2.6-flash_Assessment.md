# Assessment by mimo-2.6-flash

# Week 03 Prompting
- Awarded: 1.5b out of 5b
- Commentary: Task 1 is fully delivered: three non-ROSES frameworks (RTF, RISE, ICIO) with formulated prompts and a source/rationale report. Task 2 delivers complete per-prompt prediction sets (155 questions each) and an evaluation script, but the prediction files carry no model/prompt metadata or timing columns and the report exists only as a PDF that this model could not open, so its comparison, visualisation and inference-time claims could not be verified. Tasks 3 and 4 contain no student deliverables beyond the assignment statements themselves, so they receive no credit.

## Task 1
- Awarded: 1b   (max 1b)
- Commentary: Three prompts (RTF, RISE, ICIO) are formulated in separate files, correctly avoiding the prohibited ROSES and zero-shot frameworks, and each targets the Task 2 SQL-generation problem with an explicit expected output format. The report explains in one line per framework why it was chosen, what was expected from it, and states the source (https://frompting.com/frameworks, as given in the instructions). The rationales are terse but meet the stated requirements, so full credit is given.

## Task 2
- Awarded: 0.5b   (max 1b)
- Commentary: Present: three full prediction files (RTF/RISE/ICIO, 155 questions each with a distinct per-framework query style), the dataset/schema/labels, an evaluation script that builds an SQLite DB and scores row-multiset accuracy, and a Report.pdf. Deductions: the data files contain only `question,predicted_sql` — no model identification and prompt identification only via filename — and no inference-time measurements appear anywhere in the text files; the report (which presumably holds the comparison, visualisation and timings) is a PDF that this model cannot view, so its content could not be verified and is judged only by its presence. Substantial but incomplete/underspecified work.

## Task 3
- Awarded: 0b   (max 1b)
- Commentary: No deliverables exist for Task 3: the folder contains only the unmodified assignment statement. No new metric is proposed, argued, implemented, or computed over the Task 2 predictions, and no comparison report exists. The evaluation script in Task_2/data implements the original accuracy metric, not a novel one.

## Task 4
- Awarded: 0b   (max 2b)
- Commentary: No deliverables exist for Task 4: only the unmodified assignment statement is present. There is no detailed report, no tables or graphs of metric values, no statistical-significance testing, and no analysis treating prompt, model and coding agent as factors.