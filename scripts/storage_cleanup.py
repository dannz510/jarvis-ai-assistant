import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.policy import PolicyOrchestrator
from Security import audit
from core.config import get_config

def run_cleanup(dry_run: bool = False) -> dict:
    """Run storage cleanup programmatically.

    Args:
        dry_run: If True, only preview what would be cleaned without making changes.

    Returns:
        Dictionary with cleanup results.
    """
    cfg = get_config()
    po = PolicyOrchestrator(cfg)

    if dry_run:
        return {
            "dry_run": True,
            "retention_days_chat": cfg.retention_days_chat,
            "retention_days_metrics": cfg.retention_days_metrics,
            "message": "DRY RUN would apply policy"
        }

    res = po.apply_all()
    audit.AuditLogger().log(action="storage.cleanup", resource_type="system", meta=res, result="ok")
    return res

def main():
    """CLI entry point."""
    # Handle arguments manually to avoid argparse issues
    dry_run = "--dry-run" in sys.argv

    try:
        result = run_cleanup(dry_run=dry_run)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()