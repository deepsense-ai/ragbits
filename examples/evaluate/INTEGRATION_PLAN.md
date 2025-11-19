# Integration Plan: Moving agent_scenarios and hotel_api to evaluate

## Overview
This document outlines the plan to integrate `agent_scenarios` and `hotel_api` into the `evaluate` directory structure.

## Proposed Structure

```
examples/evaluate/
├── agent-scenarios/          # NEW: Scenario-based agent evaluation
│   ├── dataloader.py         # Load scenarios from JSON
│   ├── pipeline.py           # Evaluation pipeline for scenario testing
│   ├── metrics.py            # Task completion metrics
│   ├── run_evaluation.py     # Main evaluation script
│   ├── scenarios.json        # Test scenarios
│   └── components/          # Reusable components
│       ├── simulated_user.py
│       ├── goal_checker.py
│       └── types.py
├── fixtures/                 # NEW: Test fixtures and services
│   └── hotel-api/            # Hotel API service (moved from agents/hotel_api)
│       ├── app.py
│       ├── start_server.py
│       └── ...
└── fixtures/                 # Shared test fixtures
    └── hotel/                 # Shared hotel components
        ├── tools.py          # Hotel API tools
        └── prompt.py         # Hotel prompt template
```

## What to Move

### From agent_scenarios:
1. **Scenario-based testing framework** → `evaluate/agent-scenarios/components/`
   - `SimulatedUser` class
   - `GoalChecker` class
   - `Scenario`, `Task`, `Turn` dataclasses

2. **Scenarios data** → `evaluate/agent-scenarios/scenarios.json`
   - Keep as-is

3. **Evaluation logic** → Convert to proper evaluation pipeline
   - Create `ScenarioDataLoader` (extends DataLoader)
   - Create `ScenarioPipeline` (extends EvaluationPipeline)
   - Create `TaskCompletionMetrics` (extends Metric)

### From hotel_api:
1. **Entire directory** → `evaluate/fixtures/hotel-api/`
   - All files as-is
   - Update README to indicate it's a test fixture

### Shared Components:
1. **Hotel tools and prompts** → `evaluate/fixtures/hotel/`
   - Extract from agent_scenarios
   - Make reusable for other evaluation examples

## Integration Steps

1. Move hotel_api to fixtures
2. Create shared hotel components
3. Move and refactor agent_scenarios components
4. Create evaluation pipeline, dataloader, and metrics
5. Create main evaluation script
6. Update all imports and references

