#!/bin/bash
# Backup SQLite DB and uploads to a timestamped archive
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
ARCHIVE="$BACKUP_DIR/job-agent-backup-$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$ARCHIVE" \
  job_agent.db \
  backend/uploads/ \
  2>/dev/null || true

echo "Backup saved: $ARCHIVE"
echo "Size: $(du -sh "$ARCHIVE" | cut -f1)"
