# Diagrams

These diagrams show the current implemented paths. They omit individual model formulas, every table column, and private author-side cleaning steps so the main control flow remains readable.

## Workflow and checks

```mermaid
flowchart LR
    Run["run smoke or analyze-quant"] --> Write["write aggregate artifacts"]
    Write --> Scan["scan public output"]
    Scan --> Validate["validate files and freshness"]
    Validate --> Review["review outputs before publication"]
```

## CLI map

```mermaid
flowchart TB
    Root["genai-literacy-trial"] --> Quant["analyze-quant"]
    Root --> Legacy["build-aggregates / reproduce-paper"]
    Root --> Paper["validate-paper"]
    Root --> Privacy["audit-privacy"]
    Script["scripts/*.py wrappers"] --> Quant
    Script --> Privacy
    Script --> Hygiene["check-repo-hygiene"]
```

## Artifact lifecycle

```mermaid
stateDiagram-v2
    [*] --> Sources
    Sources --> Generated: run pipeline
    Generated --> Fresh: validator sees newer outputs
    Generated --> Stale: source or config mtime is newer
    Stale --> Generated: rerun pipeline
    Fresh --> PublishedReview: privacy and human review
    PublishedReview --> [*]
```
