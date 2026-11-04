---
type: llm
focus: trace
weight: 1
---

The assessment identifies at least five of: entities returned/bound directly in OrderController (data exposure or mass assignment); no authentication with all Actuator endpoints exposed; billing HTTP call inside the DB transaction or non-idempotent invoice creation; unbounded findAll() in isLoyalCustomer; mutable lastOrder field in a singleton bean; @Transactional on a private method; swallowed exceptions or null returns; double used for money.
