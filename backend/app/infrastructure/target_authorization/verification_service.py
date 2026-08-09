"""Target Ownership Verification Framework Service (Phase 12.5).

Implements DNS TXT challenge validation and HTTP well-known token verification.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.infrastructure.database.models.target_verification_challenge import (
    TargetVerificationChallengeModel,
)
from app.infrastructure.database.repositories.scan_target_repository import (
    ScanTargetRepository,
)
from app.infrastructure.database.repositories.target_verification_repository import (
    TargetVerificationRepository,
)
from app.infrastructure.target_authorization.dto import (
    TargetVerificationChallengeDTO,
    TargetVerificationResultDTO,
    VerificationStatus,
    VerificationType,
)

logger = get_logger("vulnova.target_verification_service")


class TargetVerificationService:
    """Enterprise service executing target ownership verification via DNS TXT and HTTP endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.target_repo = ScanTargetRepository(session)
        self.verification_repo = TargetVerificationRepository(session)
        self.audit_service = AuditLogService(session)

    async def create_challenge(
        self,
        target_id: UUID,
        organization_id: UUID,
        verification_type: VerificationType = VerificationType.DNS_TXT,
        actor_user_id: Optional[UUID] = None,
    ) -> TargetVerificationChallengeDTO:
        """Generate and persist a target ownership verification challenge."""
        target = await self.target_repo.get_target_by_id(target_id, organization_id)
        if not target:
            raise ResourceNotFoundException("Scan target not found.")

        token = f"vn_verify_{uuid4().hex}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=3)

        challenge_model = TargetVerificationChallengeModel(
            id=uuid4(),
            target_id=target_id,
            organization_id=organization_id,
            challenge_token=token,
            verification_type=verification_type.value,
            status=VerificationStatus.PENDING.value,
            created_at=now,
            expires_at=expires_at,
        )
        saved = await self.verification_repo.create_challenge(challenge_model)

        # Update target with verification token
        await self.target_repo.update_target(
            target_id=target_id,
            organization_id=organization_id,
            ownership_verification_token=token,
        )

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="target_verification.created",
            resource_type="scan_target",
            resource_id=str(target_id),
            actor_user_id=actor_user_id,
            details={
                "challenge_id": str(saved.id),
                "verification_type": verification_type.value,
                "challenge_token": token,
            },
        )

        domain = self._extract_domain(target.target_url)
        instructions = self._generate_instructions(verification_type, domain, token)

        return self._to_dto(saved, instructions=instructions)

    async def verify_target_ownership(
        self,
        target_id: UUID,
        organization_id: UUID,
        challenge_id: Optional[UUID] = None,
        actor_user_id: Optional[UUID] = None,
    ) -> TargetVerificationResultDTO:
        """Execute DNS TXT or HTTP verification check to confirm target ownership."""
        target = await self.target_repo.get_target_by_id(target_id, organization_id)
        if not target:
            raise ResourceNotFoundException("Scan target not found.")

        if challenge_id:
            challenge = await self.verification_repo.get_challenge_by_id(
                challenge_id, organization_id
            )
        else:
            challenge = await self.verification_repo.get_latest_challenge_for_target(
                target_id, organization_id
            )

        if not challenge:
            raise ValidationException(
                "No verification challenge found for target. Create a challenge first via POST /api/v1/targets/{id}/verify."
            )

        now = datetime.now(timezone.utc)
        if challenge.expires_at < now:
            await self.verification_repo.update_status(
                challenge.id, VerificationStatus.EXPIRED.value
            )
            return TargetVerificationResultDTO(
                challenge_id=challenge.id,
                target_id=target_id,
                verified=False,
                status=VerificationStatus.EXPIRED,
                message="Verification challenge token has expired. Please create a new challenge.",
            )

        domain = self._extract_domain(target.target_url)
        verified = False
        message = ""
        evidence: Dict[str, Any] = {}

        if challenge.verification_type == VerificationType.DNS_TXT.value:
            verified, message, evidence = await self._verify_dns_txt_record(
                domain=domain, expected_token=challenge.challenge_token
            )
        elif challenge.verification_type == VerificationType.HTTP_WELL_KNOWN.value:
            verified, message, evidence = await self._verify_http_well_known(
                target_url=target.target_url, expected_token=challenge.challenge_token
            )
        else:
            message = f"Unsupported verification type: {challenge.verification_type}"

        if verified:
            await self.verification_repo.update_status(
                challenge_id=challenge.id,
                status=VerificationStatus.VERIFIED.value,
                verification_metadata=json.dumps(evidence),
                verified_at=now,
            )
            await self.target_repo.update_target(
                target_id=target_id,
                organization_id=organization_id,
                is_ownership_verified=True,
                ownership_verification_token=challenge.challenge_token,
            )

            await self.audit_service.record_event(
                organization_id=organization_id,
                action="target_verification.success",
                resource_type="scan_target",
                resource_id=str(target_id),
                actor_user_id=actor_user_id,
                details={
                    "challenge_id": str(challenge.id),
                    "verification_type": challenge.verification_type,
                    "target_url": target.target_url,
                },
            )

            return TargetVerificationResultDTO(
                challenge_id=challenge.id,
                target_id=target_id,
                verified=True,
                status=VerificationStatus.VERIFIED,
                message=message,
                verified_at=now,
                evidence=evidence,
            )
        else:
            await self.verification_repo.update_status(
                challenge_id=challenge.id,
                status=VerificationStatus.FAILED.value,
                verification_metadata=json.dumps(evidence),
            )

            await self.audit_service.record_event(
                organization_id=organization_id,
                action="target_verification.failed",
                resource_type="scan_target",
                resource_id=str(target_id),
                actor_user_id=actor_user_id,
                details={
                    "challenge_id": str(challenge.id),
                    "verification_type": challenge.verification_type,
                    "target_url": target.target_url,
                    "failure_reason": message,
                },
            )

            return TargetVerificationResultDTO(
                challenge_id=challenge.id,
                target_id=target_id,
                verified=False,
                status=VerificationStatus.FAILED,
                message=message,
                evidence=evidence,
            )

    async def get_verification_status(
        self, target_id: UUID, organization_id: UUID
    ) -> TargetVerificationChallengeDTO:
        """Fetch latest verification challenge status for a scan target."""
        target = await self.target_repo.get_target_by_id(target_id, organization_id)
        if not target:
            raise ResourceNotFoundException("Scan target not found.")

        challenge = await self.verification_repo.get_latest_challenge_for_target(
            target_id, organization_id
        )
        if not challenge:
            # Create default pending DNS TXT challenge if none exists
            return await self.create_challenge(
                target_id=target_id,
                organization_id=organization_id,
                verification_type=VerificationType.DNS_TXT,
            )

        domain = self._extract_domain(target.target_url)
        instructions = self._generate_instructions(
            VerificationType(challenge.verification_type),
            domain,
            challenge.challenge_token,
        )
        return self._to_dto(challenge, instructions=instructions)

    async def _verify_dns_txt_record(
        self, domain: str, expected_token: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Query DNS TXT records for _vulnova-verify.<domain> to validate token."""
        txt_name = f"_vulnova-verify.{domain}"
        evidence: Dict[str, Any] = {
            "queried_domain": txt_name,
            "expected_token": expected_token,
        }

        try:

            def _query_dns() -> List[str]:
                try:
                    import dns.resolver  # type: ignore[import-not-found]

                    answers = dns.resolver.resolve(txt_name, "TXT")
                    records: List[str] = []
                    for rdata in answers:
                        for txt_string in rdata.strings:
                            records.append(txt_string.decode("utf-8"))
                    return records
                except Exception:
                    return []

            records = await asyncio.to_thread(_query_dns)
            evidence["dns_txt_records"] = records

            if any(expected_token in record for record in records):
                return (
                    True,
                    f"DNS TXT record '{txt_name}' successfully verified token '{expected_token}'.",
                    evidence,
                )
            else:
                return (
                    False,
                    f"DNS TXT record '{txt_name}' did not contain verification token '{expected_token}'. Records found: {records}",
                    evidence,
                )

        except Exception as err:
            logger.warning("DNS TXT query failed for %s: %s", txt_name, str(err))
            evidence["error"] = str(err)
            return (
                False,
                f"Failed to query DNS TXT record for '{txt_name}': {str(err)}",
                evidence,
            )

    async def _verify_http_well_known(
        self, target_url: str, expected_token: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Query HTTP well-known endpoint https://<domain>/.well-known/vulnova-verification.txt."""
        domain = self._extract_domain(target_url)
        verification_url = f"https://{domain}/.well-known/vulnova-verification.txt"
        evidence: Dict[str, Any] = {
            "verification_url": verification_url,
            "expected_token": expected_token,
        }

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(verification_url)
                evidence["http_status"] = resp.status_code
                evidence["body_snippet"] = resp.text[:200]

                if resp.status_code == 200 and expected_token in resp.text:
                    return (
                        True,
                        f"HTTP verification endpoint '{verification_url}' successfully returned verification token.",
                        evidence,
                    )
                else:
                    return (
                        False,
                        f"HTTP verification endpoint returned status {resp.status_code}. Token '{expected_token}' not found.",
                        evidence,
                    )

        except Exception as err:
            logger.warning(
                "HTTP verification request failed for %s: %s",
                verification_url,
                str(err),
            )
            evidence["error"] = str(err)
            return (
                False,
                f"Failed to reach HTTP verification endpoint '{verification_url}': {str(err)}",
                evidence,
            )

    def _extract_domain(self, target_url: str) -> str:
        """Extract domain host string from target URL."""
        parsed = urlparse(
            target_url if "://" in target_url else f"https://{target_url}"
        )
        host = parsed.netloc or parsed.path
        return host.split(":")[0]

    def _generate_instructions(
        self, vtype: VerificationType, domain: str, token: str
    ) -> str:
        """Generate actionable verification instructions for end users."""
        if vtype == VerificationType.DNS_TXT:
            return (
                f"Add a DNS TXT record for `_vulnova-verify.{domain}` with value `{token}`. "
                "Once published, click 'Verify Ownership' to validate."
            )
        else:
            return (
                f"Create a text file at `https://{domain}/.well-known/vulnova-verification.txt` "
                f"containing exact text `{token}`. Once accessible over HTTPS, click 'Verify Ownership'."
            )

    def _to_dto(
        self,
        model: TargetVerificationChallengeModel,
        instructions: Optional[str] = None,
    ) -> TargetVerificationChallengeDTO:
        metadata = None
        if model.verification_metadata:
            try:
                metadata = json.loads(model.verification_metadata)
            except Exception:
                metadata = {"raw": model.verification_metadata}

        return TargetVerificationChallengeDTO(
            id=model.id,
            target_id=model.target_id,
            organization_id=model.organization_id,
            challenge_token=model.challenge_token,
            verification_type=VerificationType(model.verification_type),
            status=VerificationStatus(model.status),
            verification_metadata=metadata,
            created_at=model.created_at,
            verified_at=model.verified_at,
            expires_at=model.expires_at,
            instructions=instructions,
        )
