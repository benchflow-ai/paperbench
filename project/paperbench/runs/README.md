# PaperBench Run Results

This directory contains the results of different AI agent runs attempting to reproduce research papers. Each run is organized in a timestamped directory with the following structure:

## Directory Structure

Each run directory follows this naming pattern:
```
YYYY-MM-DDThh-mm-ss-UTC_run-group_[agent-name]
```

For example:
- `2025-04-09T04-38-44-UTC_run-group_aisi-basic-agent-anthropic-dev/`
- `2025-04-09T12-51-39-UTC_run-group_aisi-basic-agent-openai-dev/`
- `2025-04-09T10-52-42-UTC_run-group_aisi-basic-agent-llama4-dev/`
- `2025-04-09T05-20-51-UTC_run-group_aisi-basic-agent-gemini-dev/`

## Run Contents

Each run directory contains:
1. `group.log` - Contains high-level information about the run execution
2. A subdirectory for each paper being reproduced (e.g., `rice_[uuid]/`)
   - `run.log` - Detailed execution log
   - `pb_result.json` - Evaluation results and metrics

## Evaluation Results

The `pb_result.json` file contains detailed evaluation metrics including:

1. Overall Score (0-1 scale)
2. Task-specific scores for different aspects of the reproduction
3. Detailed explanations for each evaluation criterion
4. Runtime information
5. Error messages (if any)

## Example Metrics

For each paper reproduction attempt, the evaluation includes:
- Code implementation correctness
- Environment setup accuracy
- Algorithm implementation fidelity
- Experimental setup compliance
- Documentation completeness

## Comparing Results

You can compare results across different agents by:
1. Looking at the overall scores in each `pb_result.json`
2. Examining the detailed task breakdowns
3. Comparing runtime performance
4. Reviewing specific implementation details in the evaluation explanations

## Notes

- Scores are on a scale of 0 to 1, where 1 indicates perfect reproduction
- Each evaluation includes detailed explanations of why certain scores were assigned
- The results include both automated and human-judged aspects of the reproduction
- Runtime information helps understand the computational efficiency of different approaches 