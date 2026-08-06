# Vulnova PostgreSQL Point-in-Time Recovery (PITR) & WAL Archiving Manual

## 1. Overview & Architecture

Point-in-Time Recovery (PITR) allows Vulnova database administrators to restore PostgreSQL data to an exact millisecond timestamp prior to data corruption, accidental drop events, or security incidents.

```text
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│  Automated Base Backup │      │  WAL Segment Archive   │      │ Point-In-Time Restore  │
│  (AES-256 Encrypted)   │  +   │ (/var/lib/postgresql/  │  =>  │ (Target Timestamp:     │
│   Daily / On-Demand    │      │  wal_archive/)         │      │  2026-08-06 14:30:00)  │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

---

## 2. PostgreSQL Configuration (`postgresql.conf`)

WAL archiving is enabled in `/etc/postgresql/postgresql.conf`:

```ini
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /var/lib/postgresql/wal_archive/%f && cp %p /var/lib/postgresql/wal_archive/%f'
archive_timeout = 60
```

---

## 3. Point-in-Time Recovery (PITR) Procedure

### Step 1: Stop Application & PostgreSQL Services
```bash
docker compose stop backend postgres
```

### Step 2: Prepare Clean Data Directory & Restore Base Backup
Extract the latest AES-256 encrypted base backup (`bkp_YYYYMMDD_HHMMSS.enc`):
```bash
# Decrypt base backup
python -c "from app.infrastructure.database.backup.encryption import backup_encryption; backup_encryption.decrypt_file('var/backups/bkp_20260806_010000.enc', 'var/backups/base_restore.sql')"
```

### Step 3: Configure Target Timestamp Recovery (`recovery.signal`)
Create `recovery.signal` file in PostgreSQL data directory:
```bash
touch /var/lib/postgresql/data/recovery.signal
```

Add recovery options to `postgresql.conf` or `standby.signal`:
```ini
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2026-08-06 14:30:00.000000+00'
recovery_target_action = 'promote'
```

### Step 4: Restart PostgreSQL & Verify Integrity
```bash
docker compose start postgres
```

Run automated restore verification via Vulnova REST API:
```bash
curl -X POST http://localhost:8000/api/v1/database/backups/verify \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>"
```

### Step 5: Resume Platform Traffic
```bash
docker compose start backend
```
