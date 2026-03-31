# Lesson Learned: refine-dev Skill Creation

**Date**: 2026-03-18
**Source**: rrr: artemis-oracle
**Tags**: skills, prompt-engineering, COSTAR, evaluation, description-optimization

## Pattern

When creating Claude Code skills, the description field is critical for triggering accuracy. A skill can be perfectly functional but never get used if its description doesn't match user language patterns.

## Key Insights

1. **Description = UX for skills**: Spend 30% of skill development time on description optimization
2. **Parallel testing scales**: Run 4+ test agents simultaneously with simulated inputs
3. **Positive framing matters**: "Use parameterized queries" triggers better than "Don't use SQL strings"
4. **Trigger phrases need variety**: Include formal ("create a prompt") and casual ("help me write a prompt for") variants

## COSTAR Framework for Mega-Prompts

The 6-step interview produces structured prompts with:
- **C**ontext (with XML delimiters)
- **O**bjective (clear task definition)
- **S**teps (reasoning strategy)
- **T**ask (specific SDLC domain)
- **A**ction (output format contract)
- **R**esult (constraints and guardrails)

## Reusable Patterns

```python
# Grading script pattern - fast assertion checks
CHECKS = {
    "uses_delimiters": lambda c: bool(re.search(r"<\w+>", c)),
    "includes_persona": lambda c: bool(re.search(r"#\s*role|you\s+are", c, re.I)),
    # ... more checks
}
```

```json
// Trigger eval format
{"query": "user prompt text", "should_trigger": true/false}
```

## Related Concepts

- skill-creator workflow
- prompt engineering
- COSTAR framework
- description optimization
- parallel agent testing
