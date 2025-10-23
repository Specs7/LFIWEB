# Repo history rewrite — collaborator notice (draft)

Hello team,

I rewrote the repository history to remove sensitive artifacts (database dumps, server logs and uploaded media). Because of that, you will need to reset your local clones to match the remote `main` branch.

Steps to sync your local clone safely:

1) If you have uncommitted local changes, stash or save them first:

   git status
   git add -A
   git stash push -m "local-work-before-history-rewrite"

2) Either re-clone or hard-reset to the new remote `main`:

   # Option A: Recloning (recommended for many contributors)
   git clone git@github.com:Specs7/LFIWEB.git

   # Option B: Hard-reset your existing clone (careful: will overwrite local commits)
   git fetch origin --prune
   git checkout main
   git reset --hard origin/main

3) For feature branches you had locally, rebase them onto the new `main` if needed:

   git checkout your-feature-branch
   git rebase --onto origin/main upstream-old-main your-feature-branch

   If this is unfamiliar, prefer to re-create the branch from the new `main`:

   git checkout -b your-feature-branch origin/main

4) If you find conflicts or lost local commits, contact me and we can help recover from `repo-backup.bundle` (I created one at the time of the rewrite).

If you want, I can also:
- Share the `repo-backup.bundle` file or a safe way to retrieve it.
- Walk you through resetting a specific local branch.

Thanks — please coordinate before pushing large or sensitive artifacts again.
