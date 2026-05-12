# Deprecated scripts

## facebook-post-cloak.mjs (2026-05-13)

Replaced by `qone_corp/social-login` package — specifically
`postFacebookFromVault` and its CLI subcommand
`bun run from-vault post-facebook --id <uuid> --page-id <id> --text "..." --image /path`.

See `docs/superpowers/specs/2026-05-13-ai-inspire-pipeline-integration.md` §D1
and §5.1 for the design decision: stealth-browser social work is owned by the
`social-login` package, not by a parallel script in artemis-oracle.

Kept in `.deprecated/` for reference only.
