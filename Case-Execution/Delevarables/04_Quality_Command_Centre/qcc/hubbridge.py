"""Bridge to the built hub (gxp-quality-hub-legacy/hub). Only PURE, deterministic hub modules are imported (no I/O, no store):

  hub.intake.validate / profiles / reasons / canon  - the real intake validation, reason precedence and natural-key identity
  hub.crosswalk.registry                             - exact-key id patterns and link types
  hub.metrics.values / sources                       - median / p90 and the strict amount parser
  app.legacy_logic                                   - the legacy priority and manual-review rules (for side-by-side display)

Nothing here writes to the repository. The hub's stateful services (store, gate, audit) are not started by this app.
"""
import os
import sys


class HubUnavailable(Exception):
    pass


class Hub(object):
    def __init__(self, repo):
        if not os.path.isdir(os.path.join(repo, "hub")):
            raise HubUnavailable("hub package not found under %s (set paths.hub_repo)" % repo)
        if repo not in sys.path:
            sys.path.insert(0, repo)
        sys.dont_write_bytecode = True  # do not leave __pycache__ files in the repository
        from hub.intake import canon, profiles, reasons, validate
        from hub.crosswalk import registry
        from hub.metrics import values, sources
        from app import legacy_logic
        self.canon, self.profiles, self.reasons, self.validate = canon, profiles, reasons, validate
        self.crosswalk, self.values, self.sources, self.legacy = registry, values, sources, legacy_logic
        self.repo = repo
        self.head = self._git_head(repo)

    @staticmethod
    def _git_head(repo):
        try:
            head = open(os.path.join(repo, ".git", "HEAD"), encoding="utf-8").read().strip()
            if head.startswith("ref:"):
                ref = head.split(" ", 1)[1]
                p = os.path.join(repo, ".git", *ref.split("/"))
                if os.path.exists(p):
                    return open(p, encoding="utf-8").read().strip()[:7]
                packed = os.path.join(repo, ".git", "packed-refs")
                if os.path.exists(packed):
                    for line in open(packed, encoding="utf-8"):
                        if line.strip().endswith(ref):
                            return line.split()[0][:7]
                return ref
            return head[:7]
        except OSError:
            return "unknown"
