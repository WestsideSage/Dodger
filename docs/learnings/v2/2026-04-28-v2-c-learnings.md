# V2-C Build a Club Learnings

- The scheduler already had functional bye support for odd club counts; the risk was documentation drift and missing coverage rather than engine plumbing.
- Fresh manager-career initialization must clear V2-A and V2-B tables together. Build a Club expanded `MANAGER_TABLES` to include recruitment tables and player trajectory data so old save artifacts cannot leak into a new career.
- Keeping expansion players as ordinary `Player` records made the weakness rule easy to test: compare top-six OVR against curated rosters and avoid any special match-engine branch.
