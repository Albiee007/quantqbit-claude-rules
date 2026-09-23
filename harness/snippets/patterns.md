# Design patterns / abstractions — checklist
Before adding any pattern, interface, base class, factory, or layer, answer:
1. Force: what CURRENT variation exists (name the real cases, not hypothetical ones)?
2. Rule of three: >= 3 real cases or an explicit external requirement?
3. Simplest alternative (function, parameter, if/switch, map of functions, composition, language feature) — why insufficient?
4. Cost: new types/files/indirection vs concrete benefit.
5. Can it be removed cheaply later?
Any weak answer -> do NOT apply the pattern; write the simple version.
If you add one, state the 5 answers in the plan/PR.
Prefer idioms: Strategy -> function param; Singleton -> injected instance; Visitor -> exhaustive switch/when/match.
Avoid: factory for one product, interface with one impl "for testing", pass-through layers, deep inheritance.
Load skill: design-patterns (mandatory gate before adding any abstraction).
