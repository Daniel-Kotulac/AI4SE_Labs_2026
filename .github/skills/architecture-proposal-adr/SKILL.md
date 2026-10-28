---
name: architecture-proposal-adr
description: "Use when analyzing software requirements to propose and compare architectures, explain trade-offs, recommend an option, or create/revise an Architecture Decision Record (ADR) and conversation notes."
argument-hint: "Requirements file or project context; optionally specify number of proposals, audience, and ADR preference"
---

# Architecture Proposals and ADRs

Guide a user from software requirements to understandable architecture options and a defensible decision record. Ground claims in the provided requirements, explain uncertain points, and produce reusable written outputs when requested.

## Workflow

### 1. Establish scope and read the evidence

1. Identify the requirement sources the user supplied: attachments, files, existing discussions, diagrams, or project documentation. Read them before proposing designs.
2. Check for relevant prior architecture conversations, ADRs, project conventions, and user preferences. Do not overwrite or silently replace existing work.
3. Summarize the system, actor roles, important user journeys, data, integrations, and quality requirements in plain language.
4. Separate **stated requirements**, **reasonable assumptions**, and **unknowns**. Do not invent traffic estimates, team size, budgets, compliance obligations, payment processing, or technology constraints.
5. Ask focused questions with the available structured question tool when an unresolved choice materially changes the architecture (for example: a hard deployment constraint, multi-seller checkout, or required consistency/availability). If proceeding with assumptions is reasonable, state them and make the recommendation provisional.

### 2. Build comparable, distinct proposals

1. Propose the number of materially different options the user requests. If no number is given and the goal is exploration, offer three credible alternatives rather than three superficial variations of one design.
2. Compare like with like. Identify whether each option describes an **application structure** (such as modular monolith or microservices), a **deployment/hosting model** (such as serverless), or another architectural dimension. These dimensions can be combined: serverless can host a modular monolith, and a monolith can run in containers. Do not present orthogonal choices as mutually exclusive without explaining the distinction.
3. For each proposal, explain:
   - a short plain-language mental model;
   - components, boundaries, ownership, and how they communicate;
   - an important end-to-end user journey and data flow;
   - how the design would be implemented, including important data/consistency behavior;
   - advantages, disadvantages, operational costs, and the painful low-level work;
   - the project conditions under which it is or is not a good fit.
4. Use a simple text diagram or comparison table when it clarifies the options. Define specialist terms on first use, especially for a non-specialist audience.
5. Discuss failure modes and correctness where the requirements make them important: authorization, concurrent updates, retries, partial failure, data ownership, recovery, and auditability. Keep guidance proportional to the request.

### 3. Recommend without overstating certainty

1. Compare options against explicit decision drivers derived from the requirements, not generic popularity.
2. Explain why the recommended option fits now, which costs it accepts, and what signals would justify revisiting it.
3. Distinguish a recommendation from an approved decision. Do not call an ADR “Accepted” unless the user or decision owner has confirmed the decision. Use **Proposed** or the repository's equivalent when approval is not established.
4. Avoid selecting specific languages, frameworks, vendors, databases, or cloud platforms unless evidence or the user requires it. Record technology choices as open decisions when appropriate.
5. Call out the most important unresolved product rules and their architectural consequences.

### 4. Explain in chat and create the requested records

1. Explain the options and recommendation directly in chat when asked; a file alone is not a substitute for an accessible explanation.
2. If the user asks for notes, create a **separate notes file for this discussion/task** rather than silently appending unrelated task discussions. Summarize faithfully; do not imply that notes are a verbatim transcript.
3. Create or update an ADR using [the ADR template](./assets/ADR_TEMPLATE.md) as a starting point. Adapt it to repository conventions and the user's requested structure. For this workflow, put **Alternatives considered at the end** unless the user or repository specifically requests another order.
4. Create conversation notes using [the notes template](./assets/CONVERSATION_NOTES_TEMPLATE.md) when requested or required by the task.
5. Use descriptive filenames in the project documentation location, and link related files to one another with repository-relative paths.
6. Preserve previous user feedback in the outputs: for example, plain-language explanations, an alternatives section at the end, or separate notes for each task. Do not reintroduce a structure the user already asked to change.

### 5. Review and verify

Before presenting the result, check that:

- every requirement and role materially relevant to the proposal is represented;
- options are genuinely distinct and their architectural dimensions are described accurately;
- the recommendation follows from stated drivers and disclosed assumptions;
- order, data, security, failure, and operational concerns are concrete where relevant;
- the ADR records context, decision, consequences, implementation implications, and revisit criteria;
- status and decision authority are honest;
- conversation notes are separate and accurate if requested;
- filenames, links, diagrams, headings, and markdown tables render coherently.

For documentation-only changes, use lightweight validation such as checking whitespace, file paths, required sections, and YAML/frontmatter only if customization files are being created. Do not claim a new-session test, user approval, or measured time saving unless it actually occurred.

## Principles learned from prior architecture work

- For systems that reserve limited inventory, identify the concurrency invariant and explain how each architecture preserves it. A single relational transaction is simpler than a distributed reservation workflow, but only when ownership and database boundaries support that transaction.
- Separate business capability boundaries from deployment topology. A queue, object store, or cloud function is optional until a requirement justifies it.
- User stories often omit important policy decisions. Make the unknowns visible instead of embedding arbitrary answers in a diagram or schema.
- A useful proposal is more than a component list: connect components to a real user journey, explain how the data changes, and surface the operational work behind the design.
- Keep recommendations appropriately provisional when team, scale, budget, or hosting evidence is missing.
