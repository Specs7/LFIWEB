# Security notes

If you accidentally committed secrets or large media files you don't want in the
repository history, rewrite history using one of these tools *locally* and then
force-push the rewritten branch to the remote (this will rewrite history for
other collaborators):

- git filter-repo (recommended):
  - https://github.com/newren/git-filter-repo
  - Example: git filter-repo --invert-paths --path backend/static/uploads/videos/largefile.mp4

- BFG Repo-Cleaner:
  - https://rtyley.github.io/bfg-repo-cleaner/

After rewriting history, `git push --force` is required. Coordinate with
collaborators; this is a destructive operation.

Also: never store SMTP credentials or SECRET_KEY in the repository. Use
PythonAnywhere Web -> Environment variables or a secrets manager.
