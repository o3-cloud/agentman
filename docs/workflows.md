# 🔀 Agentman Workflow Types

This document provides a comprehensive guide to the different workflow types supported by Agentman, their purposes, implementation patterns, and practical use cases.

## Table of Contents
- [Overview](#overview)
- [Evaluator-Optimizer](#-evaluator-optimizer)
- [Router](#-router)
- [Orchestrator](#-orchestrator)
- [Workflow Comparison](#workflow-comparison)
- [Best Practices](#best-practices)
- [Advanced Patterns](#advanced-patterns)

## Overview

Agentman supports three primary workflow types that enable different patterns of multi-agent coordination and task execution. Each workflow type is designed for specific use cases and offers unique advantages for orchestrating AI agents.

### Workflow Types Summary

| Workflow Type | Purpose | Best For | Complexity |
|---------------|---------|----------|------------|
| **Evaluator-Optimizer** | Quality improvement through iterative refinement | Content generation, code review, research validation | Medium |
| **Router** | Intelligent message routing to specialized agents | Customer support, query dispatch, model selection | Low |
| **Orchestrator** | Complex multi-step task planning and coordination | Project management, data pipelines, feature development | High |

---

## 🧪 Evaluator-Optimizer

### Purpose
The Evaluator-Optimizer workflow implements a generator + evaluator loop to iteratively improve content quality through multiple rounds of generation and evaluation.

### How It Works
1. **Generator Agent** creates initial content
2. **Evaluator Agent** assesses quality and provides feedback
3. **Loop continues** until quality criteria are met or max iterations reached
4. **Final output** represents the best iteration

### Implementation Pattern

#### Dockerfile Format
```dockerfile
# Define generator agent
AGENT content_generator
INSTRUCTION Generate high-quality marketing copy based on input requirements
MODEL anthropic/claude-3-sonnet
SERVERS web_search

# Define evaluator agent
AGENT content_evaluator
INSTRUCTION Evaluate content quality on clarity, persuasiveness, and brand alignment. Provide specific improvement suggestions.
MODEL anthropic/claude-3-opus
USE_HISTORY true

# Create evaluation chain
CHAIN quality_improvement_loop
SEQUENCE content_generator content_evaluator content_generator
CUMULATIVE true
MAX_ITERATIONS 3
```

#### YAML Format
```yaml
agents:
  - name: content_generator
    instruction: Generate high-quality marketing copy based on input requirements
    model: anthropic/claude-3-sonnet
    servers: [web_search]
  
  - name: content_evaluator
    instruction: Evaluate content quality on clarity, persuasiveness, and brand alignment. Provide specific improvement suggestions.
    model: anthropic/claude-3-opus
    use_history: true

chains:
  - name: quality_improvement_loop
    sequence: [content_generator, content_evaluator, content_generator]
    cumulative: true
    max_iterations: 3
```

### Use Cases

#### 1. Marketing Copy with Quality Control
- **Generator**: Creates initial marketing copy
- **Evaluator**: Checks brand alignment, tone, persuasiveness
- **Iteration**: Refines copy based on feedback
- **Output**: Polished, on-brand marketing material

#### 2. Automated Research Reports
- **Generator**: Compiles research findings into report format
- **Evaluator**: Validates sources, checks for gaps, ensures accuracy
- **Iteration**: Adds missing information, improves structure
- **Output**: Comprehensive, well-sourced research report

#### 3. Code Generation with Reviews
- **Generator**: Writes code based on requirements
- **Evaluator**: Reviews for best practices, security, performance
- **Iteration**: Refactors based on review feedback
- **Output**: Production-ready, reviewed code

#### 4. Prompt Engineering Experiments
- **Generator**: Creates prompts for specific tasks
- **Evaluator**: Tests effectiveness and provides optimization suggestions
- **Iteration**: Refines prompts based on performance metrics
- **Output**: Optimized, tested prompts

#### 5. Email Drafting with Tone Correction
- **Generator**: Drafts initial email content
- **Evaluator**: Assesses tone, professionalism, clarity
- **Iteration**: Adjusts tone and structure
- **Output**: Professional, well-crafted emails

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `MAX_ITERATIONS` | Maximum number of improvement cycles | 3 |
| `QUALITY_THRESHOLD` | Score threshold to stop iteration | 0.8 |
| `CUMULATIVE` | Whether to preserve context across iterations | true |
| `EVALUATOR_MODEL` | Model for evaluation (typically more powerful) | claude-3-opus |

---

## 🔀 Router

### Purpose
The Router workflow intelligently routes incoming messages to the most suitable agent based on content analysis, user intent, or predefined criteria.

### How It Works
1. **Router Agent** analyzes incoming request
2. **Classification** determines the best-suited specialist agent
3. **Routing** forwards request to selected agent
4. **Response** is returned through the router

### Implementation Pattern

#### Dockerfile Format
```dockerfile
# Define specialist agents
AGENT billing_agent
INSTRUCTION Handle billing inquiries, payment issues, and subscription management
SERVERS database payment_gateway
MODEL anthropic/claude-3-sonnet

AGENT technical_agent
INSTRUCTION Provide technical support for software issues, bugs, and troubleshooting
SERVERS github jira filesystem
MODEL anthropic/claude-3-sonnet

AGENT sales_agent
INSTRUCTION Handle sales inquiries, product demos, and pricing questions
SERVERS crm web_search
MODEL anthropic/claude-3-sonnet

# Define router
ROUTER customer_support_router
AGENTS billing_agent technical_agent sales_agent
INSTRUCTION Analyze customer inquiries and route to the appropriate specialist based on content: billing issues to billing_agent, technical problems to technical_agent, sales questions to sales_agent
MODEL anthropic/claude-3-opus
```

#### YAML Format
```yaml
agents:
  - name: billing_agent
    instruction: Handle billing inquiries, payment issues, and subscription management
    servers: [database, payment_gateway]
    model: anthropic/claude-3-sonnet
  
  - name: technical_agent
    instruction: Provide technical support for software issues, bugs, and troubleshooting
    servers: [github, jira, filesystem]
    model: anthropic/claude-3-sonnet
  
  - name: sales_agent
    instruction: Handle sales inquiries, product demos, and pricing questions
    servers: [crm, web_search]
    model: anthropic/claude-3-sonnet

routers:
  - name: customer_support_router
    agents: [billing_agent, technical_agent, sales_agent]
    instruction: Analyze customer inquiries and route to the appropriate specialist based on content
    model: anthropic/claude-3-opus
```

### Use Cases

#### 1. Customer Support Bot
- **Routing Logic**: Billing, technical, or sales categories
- **Agents**: Specialized support agents for each category
- **Benefits**: Faster resolution, expert handling, reduced training overhead

#### 2. AI Concierge for Task-Specific Routing
- **Routing Logic**: Task type analysis (research, writing, analysis, creative)
- **Agents**: Specialist agents optimized for specific task types
- **Benefits**: Optimal agent selection, improved quality, efficient resource use

#### 3. DevTool Query Dispatcher
- **Routing Logic**: Technology stack, complexity level, urgency
- **Agents**: Specialized development agents (frontend, backend, DevOps, testing)
- **Benefits**: Expert domain knowledge, faster resolution, consistent patterns

#### 4. Language-Based Routing
- **Routing Logic**: Detected language and cultural context
- **Agents**: Language-specific agents with cultural awareness
- **Benefits**: Native language support, cultural sensitivity, better user experience

#### 5. Model Selection Router
- **Routing Logic**: Task complexity, cost constraints, latency requirements
- **Agents**: Different AI models (GPT-4 for complex tasks, Claude Haiku for quick responses)
- **Benefits**: Cost optimization, performance tuning, resource efficiency

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ROUTING_MODEL` | Model used for routing decisions | claude-3-opus |
| `CONFIDENCE_THRESHOLD` | Minimum confidence for routing | 0.7 |
| `FALLBACK_AGENT` | Default agent when routing is uncertain | general_agent |
| `ROUTING_HISTORY` | Whether to consider conversation history | true |

---

## 🧩 Orchestrator

### Purpose
The Orchestrator workflow plans and coordinates complex multi-step tasks across multiple specialized agents, managing dependencies, sequencing, and overall workflow execution.

### How It Works
1. **Planning Phase**: Orchestrator analyzes the task and creates execution plan
2. **Agent Coordination**: Manages multiple agents with different specializations
3. **Dependency Management**: Ensures proper sequencing and data flow
4. **Monitoring**: Tracks progress and handles failures or iterations
5. **Integration**: Combines outputs into final deliverable

### Implementation Pattern

#### Dockerfile Format
```dockerfile
# Define specialized agents
AGENT requirements_analyst
INSTRUCTION Analyze project requirements and create detailed specifications
SERVERS database web_search
MODEL anthropic/claude-3-sonnet
USE_HISTORY true

AGENT ui_designer
INSTRUCTION Create user interface designs and mockups based on requirements
SERVERS figma_api filesystem
MODEL anthropic/claude-3-sonnet
USE_HISTORY true

AGENT backend_developer
INSTRUCTION Implement backend services and APIs according to specifications
SERVERS github database
MODEL anthropic/claude-3-sonnet
USE_HISTORY true

AGENT qa_tester
INSTRUCTION Create and execute test plans for developed features
SERVERS testing_framework github
MODEL anthropic/claude-3-sonnet
USE_HISTORY true

# Define orchestrator
ORCHESTRATOR feature_development_orchestrator
AGENTS requirements_analyst ui_designer backend_developer qa_tester
PLAN_TYPE iterative
PLAN_ITERATIONS 5
HUMAN_INPUT true
INSTRUCTION Coordinate the complete feature development lifecycle from requirements to deployment
```

#### YAML Format
```yaml
agents:
  - name: requirements_analyst
    instruction: Analyze project requirements and create detailed specifications
    servers: [database, web_search]
    model: anthropic/claude-3-sonnet
    use_history: true
  
  - name: ui_designer
    instruction: Create user interface designs and mockups based on requirements
    servers: [figma_api, filesystem]
    model: anthropic/claude-3-sonnet
    use_history: true
  
  - name: backend_developer
    instruction: Implement backend services and APIs according to specifications
    servers: [github, database]
    model: anthropic/claude-3-sonnet
    use_history: true
  
  - name: qa_tester
    instruction: Create and execute test plans for developed features
    servers: [testing_framework, github]
    model: anthropic/claude-3-sonnet
    use_history: true

orchestrators:
  - name: feature_development_orchestrator
    agents: [requirements_analyst, ui_designer, backend_developer, qa_tester]
    plan_type: iterative
    plan_iterations: 5
    human_input: true
    instruction: Coordinate the complete feature development lifecycle from requirements to deployment
```

### Use Cases

#### 1. Research → Write → Review Content Workflows
- **Phases**: Research gathering, content creation, editorial review, publication
- **Agents**: Research specialist, content writer, editor, publisher
- **Coordination**: Sequential with feedback loops, quality gates

#### 2. Feature Design from Idea to UI
- **Phases**: Ideation, requirements analysis, design, prototyping, validation
- **Agents**: Product manager, UX researcher, UI designer, prototyper
- **Coordination**: Iterative with stakeholder feedback, design validation

#### 3. Resume + Cover Letter Generator
- **Phases**: Profile analysis, job matching, document generation, optimization
- **Agents**: Profile analyzer, job matcher, resume writer, cover letter writer
- **Coordination**: Parallel processing with final integration

#### 4. Software Build → Test → Deploy Workflows
- **Phases**: Code compilation, unit testing, integration testing, deployment
- **Agents**: Build agent, test runner, deployment manager, monitoring
- **Coordination**: Sequential with failure handling, rollback capabilities

#### 5. Data Pipeline: ETL → Transform → Visualize
- **Phases**: Data extraction, transformation, loading, analysis, visualization
- **Agents**: Data extractor, transformer, loader, analyst, visualizer
- **Coordination**: Pipeline with data validation, error handling

### Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `PLAN_TYPE` | Planning strategy (sequential, parallel, iterative) | iterative |
| `PLAN_ITERATIONS` | Maximum planning iterations | 10 |
| `HUMAN_INPUT` | Whether to allow human intervention | false |
| `FAILURE_HANDLING` | Strategy for handling agent failures | retry |
| `COORDINATION_MODEL` | Model for orchestration decisions | claude-3-opus |

---

## Workflow Comparison

### When to Use Each Workflow

| Scenario | Evaluator-Optimizer | Router | Orchestrator |
|----------|---------------------|--------|--------------|
| **Single task improvement** | ✅ Ideal | ❌ Not suitable | ❌ Overkill |
| **Multiple similar tasks** | ❌ Not efficient | ✅ Perfect | ❌ Too complex |
| **Complex multi-step project** | ❌ Limited scope | ❌ Not designed for this | ✅ Designed for this |
| **Quality is critical** | ✅ Built for quality | ⚠️ Depends on routing | ✅ Can include QA |
| **Real-time responses** | ❌ Multiple iterations | ✅ Single routing | ❌ Planning overhead |
| **Resource constraints** | ⚠️ Multiple model calls | ✅ Efficient routing | ❌ Resource intensive |

### Performance Characteristics

| Metric | Evaluator-Optimizer | Router | Orchestrator |
|--------|-------------------|--------|--------------|
| **Latency** | High (iterative) | Low (single routing) | Variable (depends on plan) |
| **Cost** | Medium-High | Low-Medium | High |
| **Quality** | Very High | Depends on agents | Very High |
| **Scalability** | Medium | High | Low-Medium |
| **Complexity** | Medium | Low | High |

---

## Best Practices

### General Guidelines

1. **Choose the Right Workflow**
   - Use Router for dispatch scenarios
   - Use Evaluator-Optimizer for quality-critical tasks
   - Use Orchestrator for complex multi-agent coordination

2. **Model Selection**
   - Use more powerful models for coordinators/evaluators
   - Use cost-effective models for specialized agents
   - Consider latency requirements

3. **Error Handling**
   - Implement fallback strategies
   - Set appropriate timeouts
   - Log decision points for debugging

### Workflow-Specific Best Practices

#### Evaluator-Optimizer
- Set reasonable iteration limits to avoid infinite loops
- Use different models for generator vs evaluator
- Define clear quality criteria
- Implement early stopping conditions

#### Router
- Define clear, non-overlapping categories
- Implement confidence thresholds
- Provide fallback routing options
- Monitor routing accuracy over time

#### Orchestrator
- Break complex tasks into manageable sub-tasks
- Define clear handoff points between agents
- Implement checkpointing for long-running workflows
- Allow for human intervention at key decision points

---

## Advanced Patterns

### Hybrid Workflows

#### Router + Evaluator-Optimizer
```yaml
routers:
  - name: task_router
    agents: [simple_generator, complex_generator]
    
chains:
  - name: quality_chain
    sequence: [complex_generator, evaluator, complex_generator]
    trigger_condition: "high_quality_required"
```

#### Orchestrator with Embedded Routers
```yaml
orchestrators:
  - name: project_manager
    agents: [planner, router, implementer, reviewer]
    sub_workflows:
      - type: router
        name: implementation_router
        agents: [frontend_dev, backend_dev, mobile_dev]
```

### Conditional Workflows
```yaml
chains:
  - name: content_pipeline
    sequence: [generator, evaluator]
    conditions:
      - if: "quality_score < 0.8"
        then: [generator, evaluator]
        max_iterations: 5
      - if: "quality_score >= 0.8"
        then: [publisher]
```

### Parallel Agent Execution
```yaml
orchestrators:
  - name: parallel_processor
    agents: [agent_a, agent_b, agent_c]
    execution_mode: parallel
    synchronization_points: [validation, integration]
```

---

## Conclusion

Agentman's workflow types provide powerful patterns for orchestrating AI agents in different scenarios. By understanding the strengths and use cases of each workflow type, you can design efficient and effective multi-agent systems that solve complex problems through intelligent coordination and specialization.

For more examples and implementation details, see the `/examples` directory in the repository.