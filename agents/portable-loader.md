# Portable Agent Entry Point

This directory is the root of `skill-a-share-market-participation`.

Before answering an A-share market-participation request:

1. Load and follow [`../SKILL.md`](../SKILL.md) as the authoritative workflow.
2. Resolve all relative paths from the Skill root, not from another project or the user's home directory.
3. Use the bundled scripts and references. For live snapshots, use PandaData first and AKShare only as fallback.
4. Accept a user-provided local CSV when supplied.
5. Never search, browse, or scrape webpages for replacement market data. Fail closed when the approved sources are unavailable.
6. Treat outputs as descriptive research, not investment advice, forecasts, or promised returns.

This entry point is intended for portable runtimes such as Hermes and OpenClaw. Runtimes that natively discover `SKILL.md` should load it directly.
