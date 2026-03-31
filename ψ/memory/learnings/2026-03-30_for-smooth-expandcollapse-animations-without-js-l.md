---
title: For smooth expand/collapse animations without JS libraries, use CSS max-height w
tags: [css, animation, ui, react]
created: 2026-03-30
source: Oracle Learn
project: github.com/fiezdev/dad-asset-management-system
---

# For smooth expand/collapse animations without JS libraries, use CSS max-height w

For smooth expand/collapse animations without JS libraries, use CSS max-height with transitions: `.collapse { max-h-0 opacity-0 } .expand { max-h-[800px] opacity-100 }` combined with `transition-all duration-300`. This is more performant than React animation libraries.

---
*Added via Oracle Learn*
