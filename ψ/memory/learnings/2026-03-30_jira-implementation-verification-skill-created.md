---
title: ## Jira Implementation Verification Skill
tags: [jira, git, verification, workflow, skill]
created: 2026-03-30
source: Oracle Learn
project: github.com/bjgdr/zenith-oracle
---

# ## Jira Implementation Verification Skill

## Jira Implementation Verification Skill

Created a skill at `~/.claude/skills/jira-verify-implementation/SKILL.md` for the workflow:

1. Fetch Jira ticket details (summary, description, requirements)
2. Identify the target repository
3. Search git history for commits referencing the ticket key
4. Analyze diffs to verify requirements are met
5. Document findings in a structured comment
6. Post comment to Jira via Atlassian MCP

**Use case**: When user provides Jira URLs and wants to verify implementation, find related commits, and document the connection between requirements and code changes.

**Key commands**:
- `git log --all --oneline --grep="<TICKET-KEY>"`
- `git show <commit> --stat --format=""`

---
*Added via Oracle Learn*
