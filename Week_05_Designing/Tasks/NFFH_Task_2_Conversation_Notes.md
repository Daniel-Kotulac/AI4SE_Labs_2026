# NFFH Task 2 Conversation Notes

## Purpose

This file records the Task 2 discussion about choosing an architecture for Not Far(m) From Home (NFFH) and preparing an Architecture Decision Record (ADR). It is a summary, not a verbatim transcript.

## Context carried forward from Task 1

The NFFH requirements describe three roles—clients, agricultural companies/farmers, and administrators. Clients browse local sellers and produce, reserve products, choose pickup dates, and view orders. Farmers manage inventory and see orders. Administrators maintain users, companies, products, areas, and oversee orders.

Task 1 compared three options:

1. **Modular monolith:** one backend application separated into business modules and usually backed by one relational database.
2. **Microservices:** independently deployed services with separate ownership and service-to-service communication.
3. **Serverless managed platform:** provider-managed functions and supporting cloud services; this is a hosting/runtime approach and can host a logically modular application.

The earlier discussion recommended starting with a modular monolith because the requirements do not identify a scale, team structure, or cloud constraint that warrants more distributed complexity. It also makes the main consistency requirement—reserving limited inventory during order placement—easier to implement in one database transaction.

## Task 2 request and decision assumption

The user said Task 1 was complete, requested notes in a separate file for this conversation, and asked for an ADR based on the earlier architecture discussion.

The ADR records the modular monolith as the selected initial architecture, following the prior recommendation. This is a proposed project decision based on the available requirements; the user has not independently specified a different architecture or confirmed technology choices.

## ADR contents

The separate ADR:

- states the system context and decision drivers;
- compares the modular monolith, microservices, and serverless options;
- records the modular monolith decision and a conceptual architecture diagram;
- explains how order creation and inventory reservation should be kept consistent;
- describes module responsibilities, data and role boundaries, and consequences;
- outlines implementation and validation steps;
- lists assumptions to confirm and criteria for revisiting the decision.

The ADR deliberately avoids choosing a programming language, framework, database vendor, cloud provider, or identity provider because the project requirements do not specify them.

## ADR revision request

The user asked to move the alternative choices to the end of the ADR. The ADR was reorganized so the selected decision, architecture description, implementation guidance, consequences, revisit criteria, and references are presented before a final **Alternatives considered** section. That final section retains the summaries and trade-offs for the modular monolith, microservices, and serverless options.

## Open questions noted for later confirmation

- Does checkout allow products from multiple agricultural companies?
- Are farmers approved before their company is shown publicly?
- Are pickup selections dates only or time slots with capacity/cutoffs?
- What should cancellation do to reserved stock?
- How are seasonal or “hot” products selected?
- What personal data can administrators access, and what is the retention policy?
- What are the team's hosting, skills, availability, and expected scale constraints?

## Files created for Task 2

- ADR: `NFFH_ADR_001_Modular_Monolith.md`
- These conversation notes: `NFFH_Task_2_Conversation_Notes.md`
