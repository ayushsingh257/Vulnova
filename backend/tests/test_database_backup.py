"""Unit and Integration Test Suite for PostgreSQL Database Backup Strategy & PITR Infrastructure."""

import os
import tempfile
from uuid import uuid4
import pytest
from starlette.testclient import TestClient

from app.api.v1.dependencies.auth import get_current_user
from app.domain.entities.role import Role
from app.infrastructure.database.backup.backup_service import DatabaseBackupService
from app.infrastructure.database.backup.encryption import BackupEncryptionUtility
from app.infrastructure.database.backup.restore_verification_service import (
    RestoreVerificationService,
)
from app.infrastructure.database.models.user import UserModel
from app.security.jwt import create_access_token
from app.main import app


@pytest.fixture
def temp_backup_dir() -> str:
    temp_dir = tempfile.mkdtemp(prefix="vulnova_test_backups_")
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def backup_encryptor() -> BackupEncryptionUtility:
    return BackupEncryptionUtility(
        key_secret="test_super_secret_jwt_key_32_bytes_long_secret"
    )


@pytest.fixture
def test_backup_service(
    temp_backup_dir: str, backup_encryptor: BackupEncryptionUtility
) -> DatabaseBackupService:
    return DatabaseBackupService(backup_dir=temp_backup_dir, encryptor=backup_encryptor)


@pytest.fixture
def admin_token() -> str:
    return create_access_token(
        user_id=str(uuid4()),
        organization_id=str(uuid4()),
        role=Role.ADMIN.value,
    )


def test_encryption_utility_file_operations(
    temp_backup_dir: str, backup_encryptor: BackupEncryptionUtility
) -> None:
    """Verify AES-256 file encryption and decryption produce valid plaintext restoration."""
    plain_path = os.path.join(temp_backup_dir, "sample.txt")
    enc_path = os.path.join(temp_backup_dir, "sample.enc")
    dec_path = os.path.join(temp_backup_dir, "sample_dec.txt")

    original_content = "CREATE TABLE users (id UUID PRIMARY KEY, name VARCHAR(255));"
    with open(plain_path, "w", encoding="utf-8") as f:
        f.write(original_content)

    checksum_enc = backup_encryptor.encrypt_file(plain_path, enc_path)
    assert os.path.exists(enc_path)
    assert checksum_enc != ""

    checksum_dec = backup_encryptor.decrypt_file(enc_path, dec_path)
    assert os.path.exists(dec_path)

    with open(dec_path, "r", encoding="utf-8") as f:
        restored_content = f.read()

    assert restored_content == original_content


@pytest.mark.anyio
async def test_backup_service_creation_and_listing(
    test_backup_service: DatabaseBackupService,
) -> None:
    """Verify backup creation, file encryption, metadata generation, and retention policy listing."""
    record = await test_backup_service.create_backup(manual=True)

    assert record.backup_id.startswith("bkp_")
    assert record.status == "SUCCESS"
    assert record.is_encrypted is True
    assert record.size_bytes > 0
    assert os.path.exists(record.storage_location)

    metadata = await test_backup_service.list_backups()
    assert metadata.total_backups_count == 1
    assert metadata.total_size_bytes == record.size_bytes
    assert metadata.last_backup_at == record.timestamp


@pytest.mark.anyio
async def test_restore_verification_dry_run(
    test_backup_service: DatabaseBackupService,
    backup_encryptor: BackupEncryptionUtility,
) -> None:
    """Verify automated dry-run restore validation decrypts files and validates schema integrity."""
    verifier = RestoreVerificationService(
        b_service=test_backup_service, encryptor=backup_encryptor
    )

    record = await test_backup_service.create_backup(manual=True)
    res = await verifier.verify_restore(backup_id=record.backup_id)

    assert res.backup_id == record.backup_id
    assert res.integrity_passed is True
    assert res.schema_valid is True
    assert "users" in res.row_counts
    assert res.row_counts["users"] > 0


def test_backup_management_api_endpoints(admin_token: str) -> None:
    """Verify REST API router endpoints for listing, creating, verifying, and status checking database backups."""
    mock_admin_user = UserModel(
        id=str(uuid4()),
        organization_id=str(uuid4()),
        role="ADMIN",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user

    try:
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Trigger Backup Creation
        create_res = client.post("/api/v1/database/backups/create", headers=headers)
        assert create_res.status_code == 201
        created_data = create_res.json()
        assert created_data["status"] == "SUCCESS"
        backup_id = created_data["backup_id"]

        # 2. List Backups History
        list_res = client.get("/api/v1/database/backups", headers=headers)
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total_backups_count"] >= 1

        # 3. Verify Backup Integrity
        verify_res = client.post(
            f"/api/v1/database/backups/verify?backup_id={backup_id}", headers=headers
        )
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["integrity_passed"] is True
        assert verify_data["schema_valid"] is True

        # 4. Get Backup Operational Status
        status_res = client.get("/api/v1/database/backups/status", headers=headers)
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] == "HEALTHY"
        assert status_data["encryption"] == "AES-256"

    finally:
        app.dependency_overrides.pop(get_current_user, None)
