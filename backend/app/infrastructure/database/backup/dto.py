"""Data Transfer Objects for PostgreSQL Database Backup & PITR Management."""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BackupStatusDTO(BaseModel):
    """Metadata describing a single PostgreSQL database backup execution."""

    model_config = ConfigDict(from_attributes=True)

    backup_id: str = Field(..., description="Unique backup identifier")
    timestamp: str = Field(..., description="ISO 8601 creation timestamp")
    size_bytes: int = Field(..., description="Backup file size in bytes")
    checksum: str = Field(..., description="SHA-256 integrity checksum")
    status: str = Field(..., description="Status: SUCCESS, FAILED, IN_PROGRESS")
    storage_location: str = Field(..., description="File path or object store location")
    is_encrypted: bool = Field(
        default=True, description="Whether backup file is AES-256 encrypted"
    )


class BackupMetadataDTO(BaseModel):
    """Aggregate backup history and configuration metadata summary."""

    model_config = ConfigDict(from_attributes=True)

    backups: List[BackupStatusDTO] = Field(
        default_factory=list, description="List of recorded backups"
    )
    retention_days: int = Field(
        default=30, description="Configured retention period in days"
    )
    total_backups_count: int = Field(
        ..., description="Total number of retained backups"
    )
    total_size_bytes: int = Field(
        ..., description="Combined storage size of retained backups"
    )
    last_backup_at: Optional[str] = Field(
        None, description="Timestamp of most recent backup"
    )


class BackupVerificationDTO(BaseModel):
    """Results of automated restore dry-run and integrity verification."""

    model_config = ConfigDict(from_attributes=True)

    backup_id: str = Field(..., description="Backup identifier evaluated")
    verified_at: str = Field(..., description="ISO 8601 verification timestamp")
    integrity_passed: bool = Field(
        ..., description="True if SHA-256 checksum and AES decryption succeeded"
    )
    schema_valid: bool = Field(
        ..., description="True if database schema compatibility check passed"
    )
    row_counts: Dict[str, int] = Field(
        default_factory=dict, description="Verified table row counts"
    )
    details: str = Field(
        ..., description="Verification summary details or error description"
    )
