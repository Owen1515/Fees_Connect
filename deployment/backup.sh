#!/usr/bin/env bash
# Run as a backup service user with a protected .pgpass, never a password argument.
set -euo pipefail
umask 077
backup_dir="${BACKUP_DIR:-/var/backups/feesconnect}"
mkdir -p "$backup_dir"
backup_file="$backup_dir/feesconnect-$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump --format=custom --no-owner --file="$backup_file" "${PGDATABASE:-feesconnect}"
pg_restore --list "$backup_file" > /dev/null
# Retain thirty daily snapshots; mirror encrypted copies to offsite storage separately.
find "$backup_dir" -maxdepth 1 -type f -name 'feesconnect-*.dump' -mtime +30 -delete
