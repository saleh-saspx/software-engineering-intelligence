# Comparing look-alike patterns

Patterns that share a structure differ in intent; choose and name them by intent (DES-PAT-04). Each
comparison covers intent, structure, responsibility, when to use, cost and the signs that the wrong
one was chosen. Relations are paraphrased from S10's pattern pages (checked 2026-11-07); "wrong
choice" signals are the skill's own judgment (extension, X14).

## Contents
1. Factory Method vs. Abstract Factory · 2. Factory Method vs. Builder · 3. Strategy vs. State ·
4. Strategy vs. Template Method · 5. Adapter vs. Facade · 6. Adapter vs. Bridge · 7. Decorator vs.
Proxy · 8. Decorator vs. Adapter · 9. Observer vs. Mediator · 10. Command vs. Strategy ·
11. Composite vs. Decorator · 12. Proxy vs. Facade · 13. Chain of Responsibility vs. Decorator ·
14. Mediator vs. Facade · 15. Strategy vs. Bridge

## 1. Factory Method vs. Abstract Factory
| | Factory Method | Abstract Factory |
|---|---|---|
| Intent | One product whose type a subclass decides | A family of related products that must match |
| Structure | One overridable method inside a class with other duties (inheritance) | A separate factory object with several creation methods, passed in (composition) |
| Responsibility | The creator's main job is something else | Creating the family is the factory's only job |
| Use when | A framework or base workflow needs a varying collaborator | Several products vary together (platform, provider) |
| Cost | A creator subclass per product | Products × variants classes; a new product type touches every factory |
| Wrong choice if | Each subclass overrides several creation methods that must match → Abstract Factory | Only one product type, or one variant → Factory Method, a function or a constructor |

## 2. Factory Method vs. Builder
| | Factory Method | Builder |
|---|---|---|
| Intent | Decide which class to instantiate | Assemble a complex object step by step |
| Structure | One call returns the product | Several calls, then the product is fetched from the builder |
| Responsibility | Choose the type | Accumulate parts and enforce invariants |
| Use when | The type varies and construction is simple | Many optional parts, invariants or representations |
| Cost | A subclass per product | A builder per product, kept in sync |
| Wrong choice if | The factory method takes eight parameters → Builder or a parameter object | The builder has no optional parts or validation → constructor or factory |

## 3. Strategy vs. State
| | Strategy | State |
|---|---|---|
| Intent | Choose one of several algorithms | Behaviour follows the object's lifecycle |
| Structure | Context delegates to an interface; strategies are independent | Same delegation, but states know each other and trigger transitions (S10) |
| Responsibility | One interchangeable behaviour set from outside | All state-dependent operations plus transitions |
| Use when | A client or configuration picks the variant | The object changes its own behaviour as events happen |
| Cost | A class per variant plus selection | A class per state; transitions spread across classes |
| Wrong choice if | "Strategies" set the next strategy → State | "States" never transition and are chosen by configuration → Strategy |

## 4. Strategy vs. Template Method
| | Strategy | Template Method |
|---|---|---|
| Intent | Swap an algorithm or a part of it | Fix the skeleton, vary some steps |
| Structure | Composition: context plus strategy interface | Inheritance: base class plus overridden steps (S10) |
| Responsibility | The algorithm lives outside the context | The skeleton lives in the base class |
| Use when | Choose per object or at run time; independent variants | Stable skeleton; few steps vary; framework base classes |
| Cost | Interface and wiring | Inheritance coupling; suppressed steps risk substitution breaks |
| Wrong choice if | Each strategy duplicates the same skeleton → move the skeleton into the context or use Template Method | Subclasses override most steps or need run-time switching → Strategy |

## 5. Adapter vs. Facade
| | Adapter | Facade |
|---|---|---|
| Intent | Make an existing interface usable where another is expected | Give a subsystem a new, simpler interface |
| Structure | Usually wraps one object; implements a target the client owns | Coordinates many subsystem objects; its interface is new (S10) |
| Responsibility | Translate calls, data and errors | Orchestrate a few use cases |
| Use when | An interface mismatch at a port | Many calls in the right order for a few use cases |
| Cost | A class per adapted service | A class per subsystem; risk of a god object |
| Wrong choice if | The "adapter" orchestrates ten calls across a subsystem → Facade with adapters inside | The "facade" implements your port for a single SDK class → Adapter |

## 6. Adapter vs. Bridge
| | Adapter | Bridge |
|---|---|---|
| Intent | Retrofit compatibility between existing classes | Design two hierarchies that vary independently |
| Structure | Adapter wraps an adaptee | Abstraction holds an implementation object |
| Responsibility | Conversion | Separating high-level logic from primitives |
| Use when | After the fact, integrating existing code | Up front, when two dimensions vary (S10) |
| Cost | One adapter per adaptee | Up-front structure of two hierarchies |
| Wrong choice if | Adapters multiply for every combination of two dimensions → Bridge | The "bridge" has one implementation that converts a vendor API → Adapter |

## 7. Decorator vs. Proxy
| | Decorator | Proxy |
|---|---|---|
| Intent | Add responsibilities | Control access to the object |
| Structure | Same interface; stacks composed by the client | Same interface; often creates and manages its service itself (S10) |
| Responsibility | Extra behaviour; always delegates | May delay, deny, cache or forward remotely |
| Use when | Optional, combinable behaviours | Lazy loading, caching, access control, remoting, lifetime |
| Cost | Order-dependent stacks | Hidden costs behind an unchanged interface |
| Wrong choice if | A "decorator" sometimes doesn't delegate (denies, serves from cache) → it is a proxy | A "proxy" is stacked by clients with others to add features → decorators |

## 8. Decorator vs. Adapter
| | Decorator | Adapter |
|---|---|---|
| Intent | Same or extended interface, added behaviour | A different interface |
| Structure | Composes recursively | Does not compose recursively (S10) |
| Responsibility | Enrich | Translate |
| Use when | Add behaviour without touching clients | Fit an incompatible class |
| Cost | A class per behaviour | A class per adaptee |
| Wrong choice if | The "decorator" changes signatures or semantics → Adapter, or a defect | The "adapter" also retries and caches → split into an adapter plus decorators |

## 9. Observer vs. Mediator
| | Observer | Mediator |
|---|---|---|
| Intent | Notify an open, changing set of subscribers | Remove many-to-many dependencies by centralising coordination |
| Structure | Publisher and subscribers that come and go | Mediator knows the components; components know only the mediator; often built on Observer (S10) |
| Responsibility | The publisher does not decide reactions | The mediator decides what happens next |
| Use when | Reactions are open-ended | A fixed set of peers with complex coordination rules |
| Cost | Implicit control flow; no guaranteed order | God-object risk |
| Wrong choice if | Subscribers trigger each other in a required order → orchestrate explicitly (Mediator or a use-case service) | A mediator with one component → a direct call |

## 10. Command vs. Strategy
| | Command | Strategy |
|---|---|---|
| Intent | An operation as an object, to queue, log, defer or undo | Interchangeable ways of doing the same thing (S10) |
| Structure | Carries its parameters and receiver | Receives parameters from the context at call time |
| Responsibility | What to do — a request | How to do it — an algorithm |
| Use when | Operations must be stored, transported or undone | Algorithm variants are selected |
| Cost | History, serialisation, idempotency | Selection logic |
| Wrong choice if | "Strategies" are queued with their arguments → Command | "Commands" are never queued, logged or undone and are picked as variants → Strategy or plain functions |

## 11. Composite vs. Decorator
| | Composite | Decorator |
|---|---|---|
| Intent | Treat part–whole trees uniformly | Add responsibilities to one object |
| Structure | Many children; aggregates their results | Wraps exactly one component (S10) |
| Responsibility | Combine children | Augment the wrapped object |
| Use when | The domain is a tree | Behaviours are optional and combinable |
| Cost | Over-general interface | Order dependence |
| Wrong choice if | A composite always has one child and adds behaviour → Decorator | A "decorator" holds a list of wrapped objects → Composite |

## 12. Proxy vs. Facade
| | Proxy | Facade |
|---|---|---|
| Intent | Control access to one object behind the same interface | Simplify a subsystem behind a new interface |
| Structure | Interchangeable with its service | Not interchangeable with anything (S10) |
| Responsibility | Access control and lifecycle | Orchestration |
| Use when | Transparent control is needed | A few use cases over a complex subsystem |
| Cost | Hidden latency and I/O | God-object risk |
| Wrong choice if | The "proxy" exposes methods the service doesn't have → Facade or Adapter | The "facade" mirrors one service's interface and adds caching → Proxy or Decorator |

## 13. Chain of Responsibility vs. Decorator
| | Chain of Responsibility | Decorator |
|---|---|---|
| Intent | Let one of several handlers (or each in turn) process a request | Add behaviour around one object |
| Structure | Linked handlers; each may stop the request | Nested wrappers; each must pass the request on (S10) |
| Responsibility | Decide whether to handle or pass | Extend consistently with the base interface |
| Use when | Ordered, configurable handling, possibly ending early | Combinable behaviours that never block the call |
| Cost | Unhandled requests; tracing | Order dependence |
| Wrong choice if | A "decorator" blocks requests (auth, rate limit) → it is a handler | Every handler always passes and only adds behaviour → decorators or a plain list |

## 14. Mediator vs. Facade
| | Mediator | Facade |
|---|---|---|
| Intent | Coordinate peers so they don't know each other | Simplify access to a subsystem |
| Structure | Components refer to the mediator | Clients refer to the facade; subsystem objects may still talk directly (S10) |
| Responsibility | Adds coordination behaviour | Adds no new behaviour |
| Use when | Peers interact in many-to-many ways | Clients use a subsystem for a few use cases |
| Cost | God object | God object |
| Wrong choice if | The "facade" makes decisions about how subsystem parts react to each other → Mediator | The "mediator" only forwards client calls into a subsystem → Facade |

## 15. Strategy vs. Bridge
| | Strategy | Bridge |
|---|---|---|
| Intent | Vary one behaviour | Vary an abstraction hierarchy and an implementation hierarchy independently |
| Structure | Context plus strategy interface | Abstraction hierarchy holding an implementation hierarchy |
| Responsibility | One algorithm at a time | High-level logic over primitive operations |
| Use when | One axis of variation | Two axes that would multiply subclasses |
| Cost | Selection | Two hierarchies to keep coherent |
| Wrong choice if | The context is itself subclassed per variant of a second dimension → Bridge | The implementation side has a single member → Strategy or no pattern |
