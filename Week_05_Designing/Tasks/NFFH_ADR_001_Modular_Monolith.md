# ADR 001: Use a Modular Monolith for NFFH

- **Status:** Proposed
- **Date:** 2026-10-27
- **Decision owners:** NFFH project team

## Context

Not Far(m) From Home (NFFH) is a platform connecting consumers with local agricultural companies. Consumers discover sellers and produce, manage a cart, select a pickup day, place reservations, and view their orders. Farmers manage their company information and inventory and review orders. Administrators manage users, companies, areas, products, and platform orders.

The requirements describe pickup reservations, not online payments. They do not specify expected traffic, team size, deployment platform, pickup slot rules, seller approval, cancellation behavior, or whether a cart may contain items from several sellers. The initial architecture should therefore avoid committing to complexity that is not justified by known requirements, while preserving data consistency for the core order flow.

The main architectural challenge is safely handling inventory. A product may have limited stock, and concurrent checkout attempts must not reserve more than is available. The system also needs role- and ownership-aware authorization for three roles: client, farmer, and administrator.

## Decision drivers

1. Keep initial development, deployment, testing, and operation manageable.
2. Keep order creation and inventory reservation consistent and auditable.
3. Support clear separation of consumer, farmer, and administrator capabilities.
4. Avoid premature distributed systems complexity without known scale or team needs.
5. Leave a path to evolve hosting or extract modules later if evidence supports it.

## Decision

Build the initial NFFH backend as a **modular monolith**, with a responsive web client, one backend application organized by business capability, and a relational database as the source of truth for transactional data.

The backend modules should have explicit responsibilities and avoid reaching into each other's internals:

- **Identity and Accounts:** registration, authentication/session integration, profiles, roles, and account status.
- **Seller Directory and Areas:** agricultural company profiles, locations, area membership, and publication/approval status.
- **Catalog and Inventory:** product details, seasonal/highlight status, seller ownership, and available quantities.
- **Cart and Orders:** cart operations, pickup selection, order lifecycle, order history, and stock reservation.
- **Administration and Reporting:** authorized user/company/product/area maintenance, order oversight, and audit records.

The website can present role-appropriate pages for clients, farmers, and administrators while calling a versioned backend HTTP API. The backend remains authoritative for authorization, validation, prices, quantities, pickup rules, and order state.

```text
 Client browser       Farmer browser       Admin browser
       \                    |                   /
        +---------- Responsive web client ------+
                             |
                     Versioned HTTP API
                             |
                 +-----------+------------+
                 | Modular backend        |
                 |                        |
                 | Accounts               |
                 | Seller Directory/Areas |
                 | Catalog/Inventory      |
                 | Cart/Orders            |
                 | Administration         |
                 +-----------+------------+
                             |
                    Relational database
                             |
                 Optional object storage
                 and background job/queue
```

The diagram is conceptual. The API and modules may be deployed together; object storage and a queue are optional supporting services, not prerequisites for the core architecture.

## Order and inventory consistency

Order submission must revalidate all authoritative data on the server. The backend should check that the client is permitted to place the order, each product is active and belongs to the expected seller, the current price is valid, requested quantities are available, and the pickup date is allowed.

Order creation and inventory reservation should be performed atomically in a database transaction. Use appropriate row locking or a conditional stock update so concurrent checkouts cannot reserve more stock than exists. If any validation or reservation fails, the transaction must not leave a partial order behind. The database should enforce relevant constraints as an additional safeguard.

Order lines should retain snapshots of product name and price at order time so later catalog changes do not alter historical records. Define order statuses and allowed transitions, and decide how cancellations release reserved stock. If notifications are added, send them after the order transaction is committed; notification failure must not undo a valid reservation.

## Data and access boundaries

Use a relational model for users, agricultural companies, areas, products/inventory, orders, and order lines. An order belongs to a client and a seller (or is split into seller-specific orders if multi-seller checkout is later supported). Product ownership must be checked on every farmer inventory change.

Authorization is enforced by backend policy checks:

- Clients can access their own profile, cart, and orders.
- Farmers can maintain only their own company and products and view only orders placed with their company.
- Administrators receive only the maintenance and oversight permissions required for their duties.

Sensitive administrative actions should be audited. Disabling a malicious account should generally preserve order history and references rather than deleting records needed for business integrity. Personal information access and retention should follow a project-defined privacy policy.

## Consequences

### Positive consequences

- One application and database keep initial deployment and operations tractable.
- Database transactions make the key inventory reservation invariant easier to implement and test.
- Business modules give the codebase a structure that can be understood and evolved.
- The architecture does not require a cloud provider, message broker, or microservice platform decision up front.
- A later change can be based on measured needs rather than assumed scale.

### Negative consequences and mitigations

- **All modules deploy together.** Keep modules independently testable and avoid coupling their public interfaces to implementation details.
- **Scaling is initially coarse-grained.** Monitor response times, load, and database utilization; optimize queries and add appropriate caching or read capacity before extracting services.
- **Shared database boundaries can erode.** Assign ownership of tables and business rules to modules, use migrations, and prohibit unrelated modules from bypassing the owning module's operations.
- **Reporting can affect transactional performance.** Begin with bounded, indexed queries; add read replicas or reporting projections only when measured workloads require them.
- **A single application can have a broad failure impact.** Use health checks, structured logs, metrics, backups, graceful error handling, and automated deployment/rollback procedures.

## Implementation outline

1. Confirm domain rules: farmer approval, seller scope of a cart/order, pickup dates or slots, cancellation and stock release, order statuses, seasonal product definition, and account deletion/retention.
2. Define role permissions, module interfaces, relational schema, database constraints, and transactional inventory rules.
3. Implement account/session flows and seller/area profiles.
4. Implement seller inventory management and consumer company/product discovery.
5. Implement cart, checkout, stock reservation, and client/farmer order history.
6. Implement administrator maintenance and reporting with audit records.
7. Add optional notifications, product-image storage, monitoring, backups, and map-direction links as requirements warrant.
8. Validate with automated tests for role boundaries, seller ownership, concurrent checkout for scarce inventory, retry behavior, invalid pickup dates, cancellations, and historical price snapshots.

Technology choices (programming language, framework, database hosting, identity provider, and deployment platform) are intentionally left open. They should be selected based on the team's skills, hosting constraints, and deployment requirements rather than inferred from the user stories.

## Revisit criteria

Revisit this decision if one or more of the following become true:

- Independent teams need to release capabilities on different schedules.
- A module has a measured workload or availability requirement that cannot be met economically by scaling the whole application.
- Deployment coupling is repeatedly blocking delivery.
- A hosting requirement strongly favors managed functions or another runtime model.
- Data volume or reporting needs require a separate read model.

Any extraction should preserve clear data ownership and explicitly define how order/inventory consistency is maintained across the new boundary.

## References

- NFFH requirements: `data/NFFH.txt`
- Task 1 architecture discussion: `NFFH_Architecture_Notes.md`

## Alternatives considered

### Modular monolith — selected

One backend application is divided into explicit business modules and deployed as a unit. A relational database is the transactional source of truth.

**Benefits:** lowest operational overhead of the options; straightforward local development and end-to-end testing; order creation and stock reservation can use one database transaction; module boundaries still provide code organization.

**Costs:** modules are generally released together; scaling is coarse-grained; poor boundary discipline can create tight coupling; reporting may eventually compete with transactional workloads.

### Domain-oriented microservices — not selected initially

Multiple independently deployed services own separate business capabilities and data. A gateway routes requests; services communicate through APIs and events.

**Benefits:** independent release and scaling; clear ownership for teams organized around services; isolation of some workload and failure domains.

**Costs:** high operational and development complexity; network failures, retries, distributed tracing, data ownership, and eventual consistency need explicit treatment. Checkout would require a reservation workflow with compensation across services instead of one database transaction. There is no stated team or scale requirement to justify these costs for the initial release.

### Serverless managed platform — not selected as the application architecture

Cloud-managed functions handle API requests, supported by managed identity, database, storage, and queue services.

**Benefits:** the provider manages much of the runtime infrastructure; automatic scaling and managed supporting services may suit variable demand.

**Costs:** provider-specific behavior and lock-in; function execution and database connection limits; distributed cloud flows can be harder to debug. The system still needs a transactional database for inventory correctness, and serverless does not remove domain or consistency design.

Serverless remains a possible hosting approach for a modular application, but it is not selected as the primary architectural structure. The project has not specified a cloud provider or operating constraints.
