from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def main() -> None:
    from eps.curation.eox_master_audit import main as eox_master_audit_main

    eox_master_audit_main()


if __name__ == "__main__":
    main()
