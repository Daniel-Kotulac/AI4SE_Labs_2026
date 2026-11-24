# Assessment by laguna-s-2.1

# Week 03 Prompting
- Awarded: 2b out of 5b
- Commentary: The student completed Task 1 (three prompting frameworks with structured prompts and a report) and Task 2 produced complete prediction CSV files for all three frameworks with well-formed SQL. However, the Task 2 Report.pdf could not be inspected because PDF input is unsupported by this model; only the data files could be verified. Tasks 3 and 4 have no student deliverables — only the assignment description files (Task_3.md, Task_4.md) are present, with no metric implementation, report, tables, graphs, or statistical analysis. Consequently Tasks 3 and 4 receive 0.

## Task 1
- Awarded: 1b   (max 1b)
- Commentary: The student selected three valid prompting frameworks from frompting.com/frameworks — ICIO, RTF, and RISE (none are ROSES or zero-shot, as required). Each framework has a corresponding prompt file (ICIO.txt, RTF.txt, RISE.txt) whose structure matches that framework's components: ICIO (Instruction/Context/Input/Output), RTF (Role/Task/Format), and RISE (Request/Input/Scenario/Expectation). report.txt explains the rationale for each choice, the expectations, and confirms the source website. This fully satisfies the Task 1 output requirements.

## Task 2
- Awarded: 1b   (max 1b)
- Commentary: Three prediction CSV files were produced (RTF_restaurants_dataset_predictions.csv, RISE_restaurants_dataset_predictions.csv, ICIO_restaurants_dataset_predictions.csv), each containing 156 question/predicted_sql rows covering all dataset questions, with prompt identification via the filename prefix. The SQL queries are well-formed, joining RESTAURANT and LOCATION tables with appropriate filters for city, food type, street name, and rating thresholds. A Report.pdf is also present, though it could not be inspected because this model does not support PDF input. The evaluate_retrieval_predictions.py evaluation script and the input data files (restaurants_dataset.csv, restaurants-schema.csv, restaurants-db.txt) are also included. The prediction data deliverables are complete.

## Task 3
- Awarded: 0b   (max 1b)
- Commentary: No deliverables were submitted. The Task_3 directory contains only the assignment description (Task_3.md). There is no proposed alternative metric, no defense of its applicability, no metric implementation source code, no calculated metric values, and no comparison report. Without any metric definition, calculation, or analysis, this task cannot be scored above 0.

## Task 4
- Awarded: 0b   (max 2b)
- Commentary: No deliverables were submitted. The Task_4 directory contains only the assignment description (Task_4.md). There is no detailed analysis of metric values across prompts, no tables, no graphs, and no statistical significance testing. Without any analysis or interpretation, this task cannot be scored above 0.
