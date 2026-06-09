# Research Mission & Evaluation Rationale

## Core Objective
Achieve a state-of-the-art solution for {{PROJECT_NAME}} by identifying a model or configuration that is both **maximally accurate** and **operationally efficient**.

## The Mission
Your goal is to optimize a complex {{SYSTEM_TYPE}} starting from {{INITIAL_STATE}}. You must identify a solution that is:
1. **Theoretically Consistent**: Adheres to the fundamental {{CONSTRAINTS/PRINCIPLES}} of the domain.
2. **Robustly Generalizable**: Performs across a wide range of {{TEST_CONDITIONS/SCENARIOS}}.
3. **Parsimonious**: Achieves the target performance with minimum unnecessary complexity.

## Evaluation Rationale
Performance is measured by a composite metric that balances multiple competing drivers:

```text
val_score = {{PRIMARY_METRIC}} 
          + {{WEIGHT_1}} * {{SECONDARY_METRIC}}
          + {{WEIGHT_2}} * {{COMPLEXITY_PENALTY}}
```

### Rationale for Metrics
- **Performance Balance**: We weight multiple metrics to ensure the solution is well-rounded and doesn't "cheat" on one aspect at the expense of another.
- **Robustness Penalty**: High variance across scenarios indicates a fragile solution. We reward consistency.
- **Complexity Penalty**: We value simplicity. A complex solution that yields only marginal gains over a simple one is often considered inferior in a research context.

## Acceptance Criteria
- **Improvement**: A candidate is only "kept" if it achieves a significantly better `val_score` than the current best.
- **Validation**: The solution must generalize to held-out test cases.
- **Physical/Logical Integrity**: The output must remain interpretable and follow known domain logic.
