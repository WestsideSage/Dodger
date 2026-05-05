# Remote Setup

This repo currently has a configured remote:

```bash
origin https://github.com/WestsideSage/Dodger.git
```

Do not replace it unless Maurice confirms the target repo should change.

If a new private GitHub remote is ever needed from a machine with an authenticated GitHub CLI, use:

```bash
gh auth status
gh repo create dodgeball-manager --private --source . --remote origin --push
git push -u origin main
git push -u origin develop
```

If `origin` already exists and should be replaced, confirm first, then use:

```bash
git remote set-url origin <new-private-repo-url>
git push -u origin main
git push -u origin develop
```
