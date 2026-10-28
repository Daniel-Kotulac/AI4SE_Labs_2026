# NFFH Architecture Conversation Notes

## What we are discussing

The user asked for an explanation in the chat of three possible architectures for Not Far(m) From Home (NFFH), and asked that notes be kept about the conversation. These notes summarize the requirements, the architecture explanations, and the practical trade-offs discussed.

## NFFH in brief

NFFH connects consumers with local agricultural companies. Farmers list fresh produce and quantities; consumers browse sellers and products, reserve produce, choose a pickup day, and collect their orders at the agricultural company. Clients and farmers can view their orders. Administrators manage users, companies, areas, products, and platform orders.

The system has three main user roles:

- **Client:** registration and sign-in, persistent session, profile, product and nearby-company browsing, cart, checkout with pickup date, location/directions, and order history.
- **Farmer / agricultural company:** registration and sign-in, persistent session, profile, inventory management, and order viewing.
- **Administrator:** sign-in, user and company maintenance, order and user review, areas management, and product maintenance.

The requirements do not describe online payment, so the proposals treat checkout as a reservation rather than payment. Other rules needing a product decision include whether one cart can contain products from multiple sellers, how pickup dates/slots are defined, whether farmers need approval, what makes a product “hot,” and how cancellations return stock to availability.

## The three architectures explained plainly

### 1. Modular monolith — one application, organized into parts

Imagine one well-organized shop with different departments. Customers, farmers, and admins use the same website, and one backend application handles all their requests. Inside that backend, code is divided into modules such as Accounts, Companies, Products/Inventory, Orders, and Administration. The modules are organized separately, but they are released and run as one application. They usually share one relational database.

When a client places an order, the Orders module can check product availability, record the order, and reserve stock in one database transaction. A transaction makes these related changes succeed or fail together, which is useful when only a few units remain.

**Implementation shape:** a responsive web app; a backend exposing an HTTP API; modules with explicit responsibilities; one relational database such as PostgreSQL; and optionally object storage for product photos and a background job for notifications.

**Why it is appealing:** it is the simplest to build, test, deploy, and operate. The team can keep the code separated by domain without taking on multiple services. A single database transaction makes order/inventory consistency comparatively straightforward.

**What can hurt:** if developers ignore module boundaries, the code becomes tangled. The entire backend is generally released together, and scaling one busy part means scaling the application as a whole. As the system grows, reports can also compete with order processing for database resources.

**NFFH fit:** a sensible default for an initial version or a small team. The important discipline is to keep module ownership clear, so a later move to separate services remains possible if real needs arise.

### 2. Microservices — several independently running applications

Instead of one backend, split the system into smaller backend services, each responsible for a business area. For example, there might be an Identity service, a Seller/Area service, a Catalog/Inventory service, and an Orders service. A gateway or backend-for-frontend receives web requests and routes them to the right service. Each service owns its data and is deployed independently.

For a simple read, the gateway might retrieve seller information from the Seller service and products from the Catalog service. A checkout is harder: Orders and Inventory may own separate databases, so one ordinary database transaction cannot update both. The system needs a coordinated reservation workflow: reserve stock, create/confirm the order, and release the reservation if a later step fails. Requests and messages must be safe to retry so a timeout does not create duplicate orders or reservations.

**Implementation shape:** multiple APIs, separate data ownership, service-to-service authentication, a gateway, durable messaging/events for asynchronous work, deployment automation, and monitoring/tracing across services.

**Why it is appealing:** teams can release and scale services independently. It can suit a larger organization where different teams own different capabilities, or a system where measured traffic makes some capabilities need substantially different capacity.

**What can hurt:** network calls fail and take time; data is spread across services; retries and partial failures need careful handling. Checkout becomes a distributed workflow rather than one transaction. Local development, testing, deployment, monitoring, and administration are all more involved. Reports that combine data across services need special handling and may not be immediately up to date.

**NFFH fit:** likely excessive for a small first version unless the team already needs independent teams, scaling, or deployments. Microservices are not automatically faster or more reliable; they exchange in-process complexity for network and operational complexity.

### 3. Serverless managed platform — provider runs much of the infrastructure

The website calls API routes hosted by a cloud provider. Each route is handled by a short-lived function—for example, a function for catalog browsing or one for placing an order. The platform starts functions as needed and provides managed services for identity, database, file storage, queues, and monitoring.

“Serverless” does not mean there are no servers; it means the cloud provider manages much of their provisioning and runtime. It is also not the same thing as microservices: functions may be split by route or capability, but they can still be part of one logical application and use a shared database.

For NFFH, the order function should still use the relational database to validate availability and create the order/reserve inventory atomically. Background tasks, such as sending a confirmation notification, can run from a queue after the order is committed. Function retries must not duplicate business actions.

**Implementation shape:** a web client; managed authentication; API gateway; stateless functions; managed relational database; queue/event service for background work; object storage for images; and deployment configuration maintained as code.

**Why it is appealing:** less server maintenance and automatic scaling can make it efficient for variable or seasonal demand. Managed identity, storage, and queues can reduce the amount of infrastructure the team operates.

**What can hurt:** the design can become dependent on one provider. Functions have execution, concurrency, and database connection limits; a database still needs capacity planning. Cloud flows can be harder to debug, and local emulators do not always match production exactly. Many tiny functions can become as difficult to manage as many services.

**NFFH fit:** a reasonable option if the team prefers a managed cloud platform and understands its services. Keep order/inventory consistency in a relational database transaction; do not assume that serverless automatically solves data consistency.

## Side-by-side comparison

| Question | Modular monolith | Microservices | Serverless managed platform |
|---|---|---|---|
| How many backend deployments? | Usually one | Several independent services | Many functions/routes, usually provider-managed |
| Where does the main business data live? | One shared relational database | Data owned by separate services | Often one managed relational database at first |
| How difficult is checkout consistency? | Easiest: one database transaction | Hardest: coordinated reservation workflow | Manageable if one SQL transaction fits function limits |
| Infrastructure/operations effort | Lowest | Highest | Provider-managed but still needs cloud operations |
| Independent scaling/release | Limited | Strong | Functions scale independently within platform limits |
| Typical fit | First release, small team | Larger teams or proven independent scaling needs | Managed-cloud preference, variable traffic |

## General design points that apply whichever option is chosen

- The backend must enforce roles and ownership. Hiding buttons in the website is not security.
- Do not trust the browser for the authoritative product price, available quantity, seller ownership, or allowed pickup date.
- Validate current stock when placing an order and reserve/decrement inventory atomically. Decide how cancellations release stock.
- Preserve product name and price snapshots on order lines so later catalog edits do not rewrite old orders.
- Use an established secure session/authentication approach; logout should invalidate the session appropriately.
- Keep personal data access limited to the roles and tasks that require it, and audit sensitive admin actions.
- Product location can be stored as an address and/or coordinates; a Google Maps directions link can be constructed without embedding a map.

## Recommendation captured

For a first NFFH release, start with a **modular monolith and relational database**. It is the least complicated way to implement the reservation flow safely while keeping the code organized. Reconsider serverless hosting or extracting a service when concrete requirements—such as team ownership, measured scaling needs, or release bottlenecks—justify the added complexity.

## Conversation takeaway

The key distinction is not merely how the source code is arranged. It is how many separately running parts must communicate and who operates them. A modular monolith keeps the parts inside one application; microservices make them separate applications; serverless moves much of the runtime operation to a cloud provider and runs code in managed functions. For NFFH, the most important technical challenge in all three is accurately reserving limited produce when orders happen concurrently.
