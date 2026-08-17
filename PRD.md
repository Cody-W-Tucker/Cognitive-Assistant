# PRD

## Title

Portable Agent Bootstrap for Cognitive Assistant

## Summary

Cognitive Assistant currently generates high-value alignment artifacts: profile outputs, skills, tool specs, and agent soul-layer identity. The next product step is to turn those artifacts into a portable agent runtime that can be installed on any Nix-enabled system with one command.

This project will extend the current synthesis pipeline into a bootstrap and packaging pipeline. The system will:

1. Build compressed identity and operational artifacts up front.
2. Import user-preconfigured harnesses like Opencode and Hermes into this flake.
3. Wire in bridge resources like skills, agent souls, docs, memories, calendars, and tasks.
4. Export installable harness packages with prompts, skills, agent souls, and tool specs preconnected.
5. Support one-command bootstrap on a fresh machine.

The product outcome is not just better prompts. It is a portable, reproducible, user-shaped agent system.

## Problem

The repo is already strong at generating the mind of the agent:

- existential profile for identity and drives
- operational profile for tactics and tool behavior
- soul and alignment artifacts for coherence
- skill and tool-spec generation for downstream use
- agent-soul and alignment generation for downstream use

What is missing is a durable way to rehydrate the whole system on a new machine without manually reconstructing:

- runtime assumptions
- harness wiring
- auth and secret expectations
- mutable bridge resources
- activation steps
- health and readiness checks

Today, the repo produces artifacts. It does not yet produce a complete installable agent runtime.

## Product Vision

Generate a portable agent package that preserves the user's identity, operational patterns, bridge resources, and harness integrations so a fresh machine can become an operable agent environment with one command.

## Goals

1. Package generated identity artifacts for downstream harnesses.
2. Import and configure pre-existing user harnesses through the flake.
3. Separate immutable generated artifacts from mutable user state.
4. Make machine readiness explicit through status and health checks.
5. Allow a new Nix system to bootstrap the agent in one command.
6. Preserve the current profile-based architecture rather than replacing it.

## Non-Goals

1. Replacing Opencode, Hermes, or other harnesses.
2. Storing plaintext secrets inside generated repo artifacts or exported packages.
3. Building a universal agent runtime for every host type in the first version.
4. Designing a new identity-generation pipeline from scratch.
5. Solving long-term autonomous memory syncing in V1.

## Users

### Primary user

The owner-operator who already has:

- a Cognitive Assistant profile generation workflow
- one or more preferred agent harnesses
- external tools and docs that act as the working bridge with the agent

### Secondary user

A future downstream system or collaborator who installs the packaged agent on another machine and needs a predictable setup path.

## Core Product Idea

The current repo generates compressed reminder artifacts that tell the agent who it is and how it should operate. This feature adds the missing body: packaging, runtime wiring, state boundaries, and machine bootstrap.

The resulting system will have four layers:

1. Identity layer
   `SOUL.md` (orchestrator translation-layer constitution),
   `INTERACTION_POSTURE.md` (inferred archetype), `persona_map.md`,
   per-agent souls in `agents/<slug>.md`, `alignment_spec.md`, related
   prompts.
2. Operational layer
   Generated skills, tool specs, operational human profile, action patterns.
3. Bootstrap layer
   Machine-readable manifest, package exports, activation logic, readiness checks.
4. Mutable bridge layer
   User docs, memories, calendar access, task systems, auth state, local overrides.

## UX Flow

1. The project builds bootstrap artifacts up front.
   Outputs include agent souls, skills, human profiles, tool specs, and a machine-readable bootstrap manifest.

2. The flake imports user-preconfigured harnesses.
   Harnesses like Opencode and Hermes bring minimal mutable config plus batteries-included support for auth, MCPs, CLI tools, and provider wiring.

3. The system binds bridge resources.
   Skills, agent souls, external docs, memories, calendars, and task systems form the user-agent bridge. Some are read-only; some are read/write.

4. The flake exports harness packages.
   Each exported package has prompts, skills, agent souls, tool specs, and bridge bindings wired into the target harness shape.

5. On any compatible system, the user installs Nix and runs one command.
   The command installs or activates the packaged agent runtime, verifies the environment, and reports any missing secrets or mounts.

## Product Principles

1. Generated identity is immutable until regenerated.
2. User state is mutable and must survive reinstall and upgrade.
3. Prompts describe identity and judgment, not filesystem and secret wiring.
4. Runtime wiring belongs in manifests and package assembly.
5. Bootstrap success must be machine-verifiable.
6. Fresh-machine setup must fail clearly, not opaquely.

## Functional Requirements

### 1. Bootstrap artifact generation

The pipeline must generate a new bootstrap artifact set after existing profile artifacts are built.

Required outputs:

- `agent_manifest.json`
- `BOOTSTRAP.md`
- `status schema` or equivalent machine-readable readiness contract

These must be generated from existing outputs rather than hand-maintained duplicates where possible.

### 2. Harness import and assembly

The flake must be able to import one or more user harnesses and assemble a runtime package for each supported harness target.

Initial targets:

- Opencode
- Hermes

Harness packages must support:

- prompt injection or attachment
- skill mounting
- agent soul mounting
- tool spec mounting
- bridge resource mounting
- minimal mutable local config

### 3. Mutable vs immutable boundary

The system must define and enforce the difference between:

- generated immutable artifacts
- imported harness code and templates
- machine-local secrets and auth
- mutable user memory and bridge state

Rebuilds must not overwrite mutable bridge state.

### 4. Bridge resource registration

The system must support a registry or manifest section for external resources such as:

- docs
- notes
- memory stores
- calendars
- tasks
- MCP endpoints
- CLI tools

Each bridge resource should declare:

- name
- type
- access mode: read-only or read-write
- expected mount or integration point
- auth source
- health check behavior

### 5. One-command bootstrap

The system must expose a single command path for fresh-machine installation.

Example shape:

```bash
nix run .#bootstrap-agent
```

The command must:

1. verify prerequisites
2. activate the selected harness package
3. check required secrets/config
4. validate mounts and resources
5. report final readiness state

### 6. Bootstrap status

The system must provide a status check that answers:

- what is already present
- what is missing
- what can be repaired automatically
- what requires user action

This should exist both as a CLI command and as machine-readable output.

### 7. Regeneration semantics

The product must document and implement what happens when:

- soul changes
- human profiles change
- skills are regenerated
- agent souls are regenerated
- tool specs change
- harness packages update
- mutable bridge data changes

The expected behavior is selective rebuild, not full destructive replacement.

## Proposed Artifacts

### Generated artifacts

- `workspaces/alignment/artifacts/INTERACTION_POSTURE.md`
- `workspaces/alignment/artifacts/SOUL.md`
- `workspaces/alignment/artifacts/persona_map.md`
- `workspaces/alignment/artifacts/agents/<slug>.md`
- `workspaces/skills/<profile>/<skill>/SKILL.md`
- `workspaces/<profile>/artifacts/human_profile*.md`
- `workspaces/operational/artifacts/tool_specs/*.md`

### New bootstrap artifacts

- `workspaces/bootstrap/artifacts/agent_manifest.json`
- `workspaces/bootstrap/artifacts/BOOTSTRAP.md`
- `workspaces/bootstrap/artifacts/status.schema.json` or equivalent

### Exported flake outputs

- `packages.<system>.agent-opencode`
- `packages.<system>.agent-hermes`
- `apps.<system>.bootstrap-agent`
- `apps.<system>.bootstrap-status`

## Proposed Manifest Shape

The exact schema can evolve, but V1 should include:

```json
{
  "agent": {
    "name": "cognitive-assistant",
    "version": "v1",
    "profiles": ["existential", "operational", "alignment"]
  },
  "identity": {
    "soul": "path-or-store-ref",
    "archetype": "path-or-store-ref",
    "humanProfiles": ["path-or-store-ref"]
  },
  "operational": {
    "agentSoulsDir": "path-or-store-ref",
    "skillsRoot": "path-or-store-ref",
    "toolSpecs": {
      "memory": "path-or-store-ref",
      "tasks": "path-or-store-ref"
    }
  },
  "harnesses": {
    "opencode": {
      "enabled": true,
      "package": "flake-output-ref"
    },
    "hermes": {
      "enabled": true,
      "package": "flake-output-ref"
    }
  },
  "bridges": [
    {
      "name": "calendar",
      "type": "external-service",
      "access": "read-write",
      "auth": "machine-local",
      "required": false
    }
  ],
  "environment": {
    "requiredEnv": [],
    "requiredPaths": [],
    "requiredTools": ["nix"]
  },
  "bootstrap": {
    "command": "nix run .#bootstrap-agent",
    "statusCommand": "nix run .#bootstrap-status"
  }
}
```

## Proposed CLI Additions

New commands under `python -m core`:

- `build-bootstrap`
- `bootstrap-status`
- `build-harness-package --target opencode|hermes`

Responsibilities:

- `build-bootstrap`
  Generates the manifest and bootstrap documentation from current artifacts.

- `bootstrap-status`
  Reports machine readiness, missing config, missing mounts, and unresolved bridge dependencies.

- `build-harness-package`
  Produces harness-shaped outputs and wiring metadata for flake export.

## Proposed Repository Additions

### New code

- `core/bootstrap_creator.py`
- `core/bootstrap_status.py`
- `core/harness_packager.py`

### New profile or config area

One of these approaches:

1. Keep bootstrap as a cross-profile artifact builder under `core/` only.
2. Add `profiles/bootstrap/` if prompt-backed synthesis becomes substantial.

V1 recommendation:

Keep bootstrap as a cross-profile artifact builder first. Only add a dedicated profile if prompt complexity grows enough to justify it.

### New workspace area

- `workspaces/bootstrap/artifacts/`
- `workspaces/bootstrap/state/` if a tracked state ledger is needed

## Packaging Model

### Harness package exports

Each harness package should expose:

- generated prompts or prompt attachments
- mounted skill tree
- mounted agent soul tree
- tool specs
- harness-specific config fragments
- bootstrap metadata

### Secret handling

Secrets must not be embedded in generated artifacts or immutable flake store outputs.

Instead:

- package exports declare required secret names and locations
- activation reads secrets from machine-local configuration
- `bootstrap-status` reports missing secrets clearly

### Mutable local state

Mutable state should live outside immutable generated package outputs.

Examples:

- auth tokens
- memory databases
- task sync files
- local knowledge overlays

## System Boundaries

### Immutable generated layer

- soul
- human profiles
- skills
- agent souls
- tool specs
- bootstrap manifest
- package assembly metadata

### Mutable machine-local layer

- API keys
- OAuth tokens
- MCP auth state
- writable memory stores
- task and calendar local sync/cache
- local user overrides

The system must not blur these layers.

## Success Criteria

### Product success

1. A fresh Nix-enabled machine can install and activate a packaged harness in one command.
2. The installed harness can access generated prompts, skills, agent souls, and tool specs without manual copying.
3. The system reports exactly what is missing when not ready.
4. Rebuilding identity artifacts does not destroy mutable bridge state.
5. At least one harness target works end to end in V1.

### Technical acceptance criteria

1. `python -m core build-bootstrap` produces a valid manifest and bootstrap doc.
2. `nix flake show` exposes bootstrap-related apps and packages.
3. `nix run .#bootstrap-status` returns machine-readable readiness output.
4. `nix run .#bootstrap-agent` performs activation or exits with explicit blockers.
5. Opencode support works end to end before Hermes is considered complete.

## Milestones

### Milestone 1: Bootstrap spec

- define manifest schema
- define mutable vs immutable boundaries
- define readiness model
- generate `BOOTSTRAP.md` and `agent_manifest.json`

### Milestone 2: Status and activation

- add `bootstrap-status`
- add initial activation flow
- wire secret checks and environment validation

### Milestone 3: First harness target

- implement Opencode package export
- mount prompts, skills, agent souls, and tool specs
- verify end-to-end bootstrap on a fresh machine

### Milestone 4: Second harness target

- implement Hermes package export
- normalize shared packaging logic

## Risks

1. Overloading prompts with configuration responsibilities.
2. Mixing mutable bridge data into immutable package outputs.
3. Tight coupling to one harness without a general packaging contract.
4. Secrets accidentally leaking into generated artifacts or flake outputs.
5. One-command bootstrap becoming opaque if status reporting is weak.

## Open Questions

1. Should harness config fragments live in this repo or be imported from separate flake inputs?
2. Is bridge resource registration static, generated, or partially user-authored?
3. Should `bootstrap-status` be pure inspection or allowed to repair simple issues?
4. What is the stable location for mutable local state across target systems?
5. Does V1 support only NixOS, or any machine with Nix installed?

## Recommended V1 Scope

Build the smallest end-to-end slice that proves the model:

1. Generate `agent_manifest.json` and `BOOTSTRAP.md`.
2. Add `build-bootstrap` and `bootstrap-status`.
3. Export one harness package: Opencode.
4. Support one-command bootstrap on a fresh machine with explicit secret and dependency checks.
5. Leave Hermes and richer bridge sync behavior for after the first successful install path.

## Why This Fits The Current Project

This direction is a direct extension of the existing architecture.

The repo already knows how to synthesize:

- identity
- operational patterns
- alignment
- skill outputs
- agent soul outputs
- tool specs

The new work adds the missing deployment layer:

- packaging
- bootstrap manifests
- readiness inspection
- harness assembly
- system activation

In short:

The current project generates the mind of the agent.
This PRD extends it to generate the body and installation path too.
