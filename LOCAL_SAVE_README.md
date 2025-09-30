This repository snapshot was saved locally instead of pushing workflow changes to remote.

- Date: 2025-09-19
- Reason: Remote push rejected because the Personal Access Token lacked `workflow` scope.
- Contents: Local commit includes code changes to `benson_rsi_bot.py`, formatter configs, and `dashboard.py`.

Usage:
- To restore into another git repo or import elsewhere:
  git bundle verify local_repo_snapshot.bundle
  git clone local_repo_snapshot.bundle -b main <destination>
