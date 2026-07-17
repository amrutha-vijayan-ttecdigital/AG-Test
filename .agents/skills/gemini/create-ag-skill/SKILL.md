---
name: create-ag-skill
description: Guide for creating effective custom Antigravity skills. This skill should be used when the user wants to create a new skill (or update an existing skill) that extends Antigravity's capabilities with specialized knowledge, workflows, or tool integrations.
---

# create-ag-skill

This skill provides guidance and scaffolding tools for creating effective custom skills in this workspace.

## About Skills

Skills are modular, self-contained directories under `.agents/skills/gemini/` that extend Antigravity's capabilities by providing specialized knowledge, workflows, and tools. They equip the agent with procedural knowledge and scripts to execute complex domain-specific tasks.

### Anatomy of an Antigravity Skill

Every skill consists of a required `SKILL.md` file and optional resource subdirectories:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation loaded into context as needed
    └── assets/           - Non-doc files used in output (templates, icons, boilerplates)
```

#### 1. SKILL.md (required)
Contains the trigger metadata and core procedural guidance:
* **Frontmatter** (YAML): Contains `name` and `description` fields. These are read by Antigravity to determine when to trigger the skill. Keep the description clear and explicit about when to use the skill.
* **Body** (Markdown): Procedural instructions. Keep this under 500 lines to avoid context window bloat. Use references/ for detailed guides or documentation.

#### 2. Scripts (`scripts/`)
Executable helper scripts. Use these for fragile, complex, or repetitive code tasks to ensure deterministic reliability.

#### 3. References (`references/`)
Reference documentation (e.g. schemas, API specifications) that is loaded into the context window only when explicitly needed.

#### 4. Assets (`assets/`)
Boilerplates, images, or templates used in the outputs produced by the skill. Do not load these into context directly.

---

## Scaffolding a New Skill

Use the `init_skill.py` tool inside the `create-ag-skill` script directory to scaffold a new skill:

```bash
python3 .agents/skills/gemini/create-ag-skill/scripts/init_skill.py <skill-name> [options]
```

### Arguments:
* `<skill-name>`: The name of the new skill. Normalized to hyphen-case (e.g., `my-custom-skill`).
* `--resources`: Comma-separated list of resource folders to create (e.g. `scripts,references,assets`).
* `--dry-run`: Output paths that would be created without executing write operations.

---

## Validating a Skill

Use the `quick_validate.py` script to verify that a skill folder meets the required structure:

```bash
python3 .agents/skills/gemini/create-ag-skill/scripts/quick_validate.py <path-to-skill-folder>
```

It validates:
1. `SKILL.md` exists and contains correct YAML frontmatter.
2. Frontmatter contains both `name` and `description`.
3. Folder name matches the frontmatter `name`.
