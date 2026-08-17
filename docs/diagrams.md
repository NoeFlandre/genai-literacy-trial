# Repository Diagrams

These Mermaid diagrams summarize the current repository structure and workflow. They intentionally omit most test files, individual table names, and model formulas so the diagrams stay maintainable; those details are documented in `docs/artifacts.md`, `docs/data_flow.md`, and `docs/repo_map.md`.

## High-Level Architecture

```mermaid
flowchart LR
    subgraph EntryPoints["Entry points"]
        MainCli["genai-literacy-trial CLI"]
        ScriptWrappers["scripts wrappers"]
        ConsoleHelpers["smoke and hygiene console commands"]
    end

    subgraph Package["src/genai_literacy_trial"]
        Cli["cli.py"]
        Legacy["analysis.py"]
        Pipeline["quant_pipeline.py"]
        Config["quant_config.py and paths.py"]
        Preprocess["quant_preprocess.py"]
        Models["quant_models.py"]
        Stats["quant_stats.py"]
        Figures["quant_figures.py"]
        Report["quant_report.py"]
        Privacy["privacy.py"]
        Schema["quant_schema.py"]
        ReproHelpers["reproduce_small.py validate_artifacts.py repo_hygiene.py"]
    end

    MainCli --> Cli
    Cli --> Legacy
    Cli --> Pipeline
    Cli --> Privacy
    ScriptWrappers --> ReproHelpers
    ConsoleHelpers --> ReproHelpers
    ReproHelpers --> Pipeline
    Pipeline --> Config
    Pipeline --> Preprocess
    Pipeline --> Models
    Models --> Stats
    Pipeline --> Figures
    Pipeline --> Report
    Pipeline --> Privacy
    Pipeline --> Schema
```

## Quantitative Data Flow

This is the main `run_quant_analysis()` path used by `genai-literacy-trial analyze-quant` and the small reproducibility runner.

```mermaid
flowchart TB
    Inputs["survey grades prompts files"] --> ReadInputs["_read_input"]
    QuantConfig["quant_config TOML"] --> LoadConfig["load_quant_config"]
    ExpectedInventory["expected_inventory TOML optional"] --> LoadInventory["load_expected_inventory"]

    ReadInputs --> ValidateInputs["_validate_quant_input_frames"]
    LoadConfig --> ValidateInputs
    ValidateInputs --> Retain["prepare_retained_survey"]
    Retain --> Participant["build_participant_table"]
    Retain --> Composites["compute_survey_composites"]
    Participant --> MergePre["_merge_pre_composites"]
    Composites --> MergePre
    MergePre --> Assignment["build_assignment_prompt_table"]
    Retain --> PriorUse["prior_use_mapping_table"]
    MergePre --> Inventory["validate_analysis_inventory"]
    Assignment --> Inventory
    LoadInventory --> Inventory

    Inventory --> ModelTables["quant_models tables"]
    MergePre --> ModelTables
    Assignment --> ModelTables
    Composites --> ModelTables
    ModelTables --> Figures["quant_figures"]
    ModelTables --> MarkdownReport["quant_report"]
    Figures --> PublicOutputs["public output directory"]
    MarkdownReport --> PublicOutputs
    PublicOutputs --> PrivacyAudit["privacy.scan_public_tree"]
```

## Artifact Lifecycle

The public smoke workflow writes to ignored `repro_outputs/small/`. Full/private runs may target `paper_outputs/quantitative/` or private ignored directories depending on CLI options.

```mermaid
flowchart LR
    Sources["inputs config expected inventory"] --> Run["run_quant_analysis"]
    Run --> Clean["clean top-level generated public files"]
    Clean --> WriteTables["write table CSVs"]
    Clean --> WriteFigures["write PDF and PNG figures"]
    Clean --> WriteReport["write quantitative_report.md"]
    WriteTables --> PublicDir["public output directory"]
    WriteFigures --> PublicDir
    WriteReport --> PublicDir
    Run --> PrivateDir["private output directory is created"]
    PublicDir --> Audit["privacy audit"]
    PublicDir --> Validator["validate_artifacts small mode"]
    Sources --> Validator
    Validator --> Fresh["present non-empty readable not stale"]

    OldNested["nested files and other suffixes"] --> Preserved["preserved by cleanup"]
    Interrupted["interrupted run"] --> Partial["partial public outputs"]
    Partial --> Validator
```

## CLI And Module Map

```mermaid
flowchart TB
    Trial["genai-literacy-trial"] --> Analyze["analyze-quant"]
    Trial --> ReproducePaper["reproduce-paper"]
    Trial --> BuildAggregates["build-aggregates"]
    Trial --> ValidatePaper["validate-paper"]
    Trial --> AuditPrivacy["audit-privacy"]

    Analyze --> Pipeline["quant_pipeline.run_quant_analysis"]
    ReproducePaper --> Legacy["analysis.py aggregate workflow"]
    BuildAggregates --> Legacy
    ValidatePaper --> Legacy
    AuditPrivacy --> Privacy["privacy.scan_public_tree"]

    ScriptRepro["scripts/reproduce_small.py"] --> ReproModule["genai_literacy_trial.reproduce_small"]
    ConsoleRepro["genai-literacy-reproduce-small"] --> ReproModule
    ReproModule --> Pipeline
    ReproModule --> ArtifactModule["genai_literacy_trial.validate_artifacts"]

    ScriptValidate["scripts/validate_artifacts.py"] --> ArtifactModule
    ConsoleValidate["genai-literacy-validate-artifacts"] --> ArtifactModule

    ScriptHygiene["scripts/check_repo_hygiene.py"] --> HygieneModule["genai_literacy_trial.repo_hygiene"]
    ConsoleHygiene["genai-literacy-check-repo-hygiene"] --> HygieneModule
    HygieneModule --> Git["git ls-files"]
```

## Agent Workflow

This reflects the repository guidance in `AGENTS.md` and `docs/agent_playbook.md`.

```mermaid
flowchart LR
    Start["new agent task"] --> ReadDocs["read AGENTS and repo docs"]
    ReadDocs --> Inspect["inspect git status code tests docs CI"]
    Inspect --> Scope["choose smallest safe change"]
    Scope --> Edit["edit src tests docs as needed"]
    Edit --> TargetedChecks["run targeted tests"]
    TargetedChecks --> FullChecks["run ruff pytest smoke privacy checks when relevant"]
    FullChecks --> Status["inspect git status and diff"]
    Status --> Report["report verified commands and uncertainty"]

    Scope --> PrivacyRule["keep private data out of tracked files"]
    Edit --> ReproRule["use repro_outputs for generated smoke outputs"]
```
