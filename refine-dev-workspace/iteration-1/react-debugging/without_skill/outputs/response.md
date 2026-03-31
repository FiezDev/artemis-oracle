# React Performance Debugging Prompt

Here's a structured prompt you can use to debug React performance issues:

---

## Recommended Prompt

```
I'm experiencing performance issues in a React component. Please help me debug and optimize it.

**Component Context:**
- Component name: [Your component name]
- What the component does: [Brief description]
- When the issue occurs: [e.g., on mount, on interaction, during render, etc.]

**Symptoms I'm seeing:**
- [ ] Slow initial render
- [ ] Laggy interactions / slow re-renders
- [ ] High CPU usage
- [ ] Choppy animations
- [ ] Other: [describe]

**Component Code:**
[Paste your component code here]

**Current State:**
- React version: [e.g., 18.2.0]
- Using memo/memo/useMemo/useCallback: [Yes/No/Partial]
- Any third-party libraries involved: [List them]

**What I've tried (if anything):**
- [List any optimization attempts]

**Expected outcome:**
- [What performance target or behavior you're aiming for]

Please analyze the code and suggest specific optimizations, including:
1. Unnecessary re-renders and how to prevent them
2. Heavy computations that could be memoized
3. Any anti-patterns or performance pitfalls
4. Concrete code changes with explanations
```

---

## Quick Diagnostic Checklist

Before using the prompt, gather this information for faster help:

### Common React Performance Issues

| Issue | Symptom | Quick Check |
|-------|---------|-------------|
| Unnecessary re-renders | Component updates when props/state unchanged | Use React DevTools Profiler |
| Missing memoization | Heavy calculations run on every render | Check for `useMemo`/`useCallback` |
| Large re-render trees | Child components re-render unnecessarily | Add `React.memo` to children |
| Inline function props | New function created each render | Wrap in `useCallback` |
| Inline object props | New object created each render | Move outside render or memoize |
| No virtualization | Long lists render all items | Use `react-window` or similar |
| Expensive effects | Heavy work in `useEffect` | Defer with `useMemo` or Web Workers |

### Debugging Tools to Mention

- React DevTools Profiler
- `why-did-you-render` library
- Chrome Performance tab
- `console.time()` / `performance.mark()`

---

## Minimal Example

For quickest help, provide something like this:

```
My `UserList` component renders 1000 users but feels laggy when filtering.

Symptoms: Slow re-renders when filter changes
React version: 18.2.0
No memoization currently used

[Code here]

Expected: Filtering should feel instant (< 100ms)
```

---

## Pro Tips

1. **Include the parent component** if props are being passed down - the issue might be upstream
2. **Show how data flows** - where does state come from? Context? Props? API?
3. **Mention state management** - Redux, Zustand, Context, etc.
4. **Share profiler results** if you have them - flamegraphs tell the real story

---

Save this prompt template and adapt it to your specific situation. The more context you provide, the more targeted the debugging help will be.
