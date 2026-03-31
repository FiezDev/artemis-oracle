#!/usr/bin/env python3
"""Grade refine-dev skill outputs against assertions."""

import json
import os
import re
from pathlib import Path

def check_walks_all_steps(content: str) -> tuple[bool, str]:
    """Check if output walks through all 6 steps."""
    steps = [
        r"step\s*1.*persona",
        r"step\s*2.*context",
        r"step\s*3.*example",
        r"step\s*4.*output.*format",
        r"step\s*5.*reasoning",
        r"step\s*6.*constraint"
    ]
    found = sum(1 for s in steps if re.search(s, content, re.IGNORECASE))
    passed = found >= 4  # At least mention 4+ steps
    return passed, f"Found {found}/6 step references"

def check_produces_mega_prompt(content: str) -> tuple[bool, str]:
    """Check if output produces a structured Mega-Prompt."""
    has_role = bool(re.search(r"#\s*role", content, re.IGNORECASE))
    has_objective = bool(re.search(r"#\s*objective", content, re.IGNORECASE))
    has_context = bool(re.search(r"#\s*context", content, re.IGNORECASE))
    passed = has_role and (has_objective or has_context)
    return passed, f"Role: {has_role}, Objective: {has_objective}, Context: {has_context}"

def check_uses_delimiters(content: str) -> tuple[bool, str]:
    """Check if output uses XML delimiters."""
    delimiters = ["<existing_context>", "<example_input>", "<example_output>", "<code>", "<input>"]
    found = sum(1 for d in delimiters if d in content)
    passed = found >= 1
    return passed, f"Found {found} delimiter types"

def check_includes_persona(content: str) -> tuple[bool, str]:
    """Check if includes persona/role section."""
    has_persona = bool(re.search(r"(senior|junior|engineer|architect|developer|specialist)", content, re.IGNORECASE))
    has_role_section = bool(re.search(r"#\s*role|you\s+are", content, re.IGNORECASE))
    passed = has_persona and has_role_section
    return passed, f"Persona keywords: {has_persona}, Role section: {has_role_section}"

def check_includes_context_section(content: str) -> tuple[bool, str]:
    """Check if includes context section with code/background."""
    has_context = bool(re.search(r"#\s*context", content, re.IGNORECASE))
    has_delimiter = "<existing_context>" in content or "<code>" in content
    passed = has_context or has_delimiter
    return passed, f"Context header: {has_context}, Context delimiter: {has_delimiter}"

def check_includes_examples_section(content: str) -> tuple[bool, str]:
    """Check if includes examples section."""
    has_examples = bool(re.search(r"#\s*examples?|example\s*\d", content, re.IGNORECASE))
    has_io = bool(re.search(r"input.*output|<example_input>|<example_output>", content, re.IGNORECASE))
    passed = has_examples or has_io
    return passed, f"Examples header: {has_examples}, IO format: {has_io}"

def check_includes_output_format(content: str) -> tuple[bool, str]:
    """Check if includes output format specification."""
    has_format = bool(re.search(r"#\s*output\s*format|format.*specification", content, re.IGNORECASE))
    has_structure = bool(re.search(r"json|markdown|code\s*block|structured", content, re.IGNORECASE))
    passed = has_format or has_structure
    return passed, f"Format header: {has_format}, Structure mention: {has_structure}"

def check_includes_constraints(content: str) -> tuple[bool, str]:
    """Check if includes constraints section."""
    has_constraints = bool(re.search(r"#\s*constraints?|guardrails?", content, re.IGNORECASE))
    has_security = bool(re.search(r"security|validation|sanitize", content, re.IGNORECASE))
    passed = has_constraints or has_security
    return passed, f"Constraints header: {has_constraints}, Security mention: {has_security}"

CHECKS = {
    "walks_all_steps": check_walks_all_steps,
    "produces_mega_prompt": check_produces_mega_prompt,
    "uses_delimiters": check_uses_delimiters,
    "includes_persona": check_includes_persona,
    "includes_context_section": check_includes_context_section,
    "includes_examples_section": check_includes_examples_section,
    "includes_output_format": check_includes_output_format,
    "includes_constraints": check_includes_constraints,
}

def grade_output(output_path: str, assertions: list) -> dict:
    """Grade a single output file against assertions."""
    try:
        with open(output_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return {"error": f"Output file not found: {output_path}"}

    results = []
    for assertion in assertions:
        name = assertion["name"]
        if name in CHECKS:
            passed, evidence = CHECKS[name](content)
            results.append({
                "text": name,
                "passed": passed,
                "evidence": evidence
            })
        else:
            results.append({
                "text": name,
                "passed": False,
                "evidence": f"Unknown assertion: {name}"
            })
    
    return {"expectations": results}

def main():
    workspace = Path("/home/bjgdr/oracle/artemis-oracle/refine-dev-workspace/iteration-1")
    
    for eval_dir in ["python-unit-tests", "react-debugging"]:
        for config in ["with_skill", "without_skill"]:
            output_file = workspace / eval_dir / config / "outputs" / ("mega_prompt.md" if config == "with_skill" else "response.md")
            grading_file = workspace / eval_dir / config / "grading.json"
            
            if output_file.exists():
                # Load assertions from eval_metadata.json
                metadata_file = workspace / eval_dir / "eval_metadata.json"
                with open(metadata_file) as f:
                    metadata = json.load(f)
                
                result = grade_output(str(output_file), metadata["assertions"])
                
                with open(grading_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                print(f"Graded: {eval_dir}/{config}")
                passed = sum(1 for r in result["expectations"] if r["passed"])
                print(f"  Passed: {passed}/{len(result['expectations'])}")
            else:
                print(f"Output not found: {output_file}")

if __name__ == "__main__":
    main()
