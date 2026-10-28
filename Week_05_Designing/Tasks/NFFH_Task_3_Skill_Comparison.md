# Task 3: Architecture Skill Comparison

## Purpose and evidence

This report reviews the Task 1 and Task 2 conversation records and artifacts and compares the workflow with the reusable architecture skill. The user's assessment is that using the skill made the process faster, required shorter and less precise prompts, and led to fewer corrections. This is a qualitative comparison; no elapsed-time measurements or prompt-length counts were recorded, so the improvement is reported as a practical observation rather than a quantified benchmark.

## What worked in Tasks 1 and 2

- The requirements were translated into roles and core journeys for clients, farmers, and administrators.
- Three proposals explained system shape, implementation, advantages, disadvantages, and NFFH fit.
- The discussion surfaced important unknowns, including multi-seller carts, pickup scheduling, farmer approval, stock release on cancellation, and seasonal product rules.
- The recommendation connected a modular monolith to the likely initial-project context and the need for transactional inventory reservation.
- The ADR included a conceptual diagram, boundaries, consistency behavior, consequences, implementation outline, and revisit criteria.
- User feedback was applied: architecture terms were explained more accessibly, conversation records were separated by task, and the alternative choices were moved to the end of the ADR.

## What the review identified for improvement

- The three proposals were initially presented as peers even though “serverless” is primarily a hosting/runtime model, while “modular monolith” and “microservices” describe application structure. They can be combined, so comparisons should explicitly identify dimensions and avoid implying false exclusivity.
- Some business and operating constraints were unknown. The ADR appropriately left technology choices open and marked the decision Proposed, but the workflow should make this evidence/assumption distinction systematic from the start.
- A proposal should tie each architecture to a concrete NFFH flow, especially order placement and scarce-stock reservation, rather than only listing components.
- The user’s requested alternatives-at-the-end structure should be applied consistently in the ADR template rather than rediscovered through revision.
- The chat explanation and saved artifacts serve different purposes; written records should not replace a clear direct explanation when one is requested.

## How the new skill addresses these findings

| Observed need | Skill workflow support |
|---|---|
| Accurate, comparable alternatives | Requires identifying application structure versus hosting/deployment dimensions and explaining combinations |
| Evidence-based recommendation | Separates requirements, assumptions, unknowns, decision drivers, and approval status |
| Understandable architecture explanations | Requires a plain-language mental model, a user journey/data flow, and definitions for specialist terms |
| Concrete implementation and trade-offs | Requires boundaries, communication, data consistency, failure modes, operational costs, and project fit |
| NFFH inventory correctness | Calls out concurrency invariants, transactions, and distributed reservation behavior where applicable |
| Repeated ADR revisions | Provides a reusable ADR template with Alternatives considered at the end |
| Separate task records | Provides a distinct conversation-notes template and directs the assistant not to merge unrelated tasks |
| Less prompt detail and correction | Encodes the workflow, expected outputs, and lessons from prior corrections, reducing how much process guidance the user needs to repeat |

## Conclusion

Compared with the initial Task 1 and Task 2 discussions, the skill-guided process was faster in the user's assessment: the user could use shorter, less precise prompts and needed fewer corrections to guide the architecture work and ADR structure. The skill appears to help by making the workflow and prior preferences explicit, so fewer instructions need to be repeated and fewer revisions are needed. This comparison is qualitative, not a measured benchmark. The skill and templates are in `.github/skills/architecture-proposal-adr/`.
