"""Async DNS Resolver Adapter for Subdomain & DNS Intelligence.

Queries A, AAAA, CNAME, MX, NS, and TXT records using dnspython async resolver.
Classifies resolved IP addresses into PUBLIC, PRIVATE, LOOPBACK, LINK_LOCAL for enterprise ASM.
"""

from typing import Any, Dict, List, Tuple

import dns.asyncresolver
import dns.exception
import dns.resolver

from app.core.logging import get_logger
from app.domain.entities.discovery import (
    DiscoveredIP,
    DNSRecord,
    DNSRecordType,
)
from app.infrastructure.discovery.ssrf_validator import classify_ip

logger = get_logger("vulnova.dns_resolver")

DEFAULT_DNS_TIMEOUT = 5.0


class AsyncDNSResolver:
    """Async DNS record query adapter for A, AAAA, CNAME, MX, NS, and TXT records."""

    def __init__(self, timeout: float = DEFAULT_DNS_TIMEOUT) -> None:
        self.resolver = dns.asyncresolver.Resolver()
        self.resolver.timeout = timeout
        self.resolver.lifetime = timeout

    async def resolve_subdomain(self, hostname: str) -> Dict[str, Any]:
        """Resolve all DNS record types for a given hostname."""
        clean_host = hostname.strip().lower()
        records: List[DNSRecord] = []
        ip_findings: List[DiscoveredIP] = []
        cnames: List[str] = []

        # 1. A Records (IPv4)
        a_records, ips_v4 = await self._query_record_type(clean_host, DNSRecordType.A)
        records.extend(a_records)
        for ip in ips_v4:
            ip_info = classify_ip(ip)
            ip_findings.append(
                DiscoveredIP(
                    value=ip_info["value"],
                    classification=ip_info["classification"],
                    is_internal=ip_info["is_internal"],
                    is_egress_safe=ip_info["is_egress_safe"],
                )
            )

        # 2. AAAA Records (IPv6)
        aaaa_records, ips_v6 = await self._query_record_type(
            clean_host, DNSRecordType.AAAA
        )
        records.extend(aaaa_records)
        for ip in ips_v6:
            ip_info = classify_ip(ip)
            ip_findings.append(
                DiscoveredIP(
                    value=ip_info["value"],
                    classification=ip_info["classification"],
                    is_internal=ip_info["is_internal"],
                    is_egress_safe=ip_info["is_egress_safe"],
                )
            )

        # 3. CNAME Records
        cname_records, cname_vals = await self._query_record_type(
            clean_host, DNSRecordType.CNAME
        )
        records.extend(cname_records)
        cnames.extend(cname_vals)

        # 4. MX Records
        mx_records, _ = await self._query_record_type(clean_host, DNSRecordType.MX)
        records.extend(mx_records)

        # 5. NS Records
        ns_records, _ = await self._query_record_type(clean_host, DNSRecordType.NS)
        records.extend(ns_records)

        # 6. TXT Records
        txt_records, _ = await self._query_record_type(clean_host, DNSRecordType.TXT)
        records.extend(txt_records)

        return {
            "subdomain": clean_host,
            "ip_addresses": ip_findings,
            "cname_aliases": cnames,
            "dns_records": records,
        }

    async def _query_record_type(
        self, hostname: str, record_type: DNSRecordType
    ) -> Tuple[List[DNSRecord], List[str]]:
        """Query a specific DNS record type asynchronously."""
        records: List[DNSRecord] = []
        raw_values: List[str] = []

        try:
            answer = await self.resolver.resolve(hostname, record_type.value)
            ttl = getattr(answer, "ttl", None)

            for rdata in answer:
                val_str = str(rdata).strip().rstrip(".")
                raw_values.append(val_str)
                records.append(
                    DNSRecord(
                        record_type=record_type,
                        name=hostname,
                        value=val_str,
                        ttl=ttl,
                    )
                )
        except (
            dns.resolver.NoAnswer,
            dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers,
            dns.exception.Timeout,
        ):
            pass
        except Exception as err:
            logger.debug(
                "dns_resolver.query_failed",
                hostname=hostname,
                record_type=record_type.value,
                error=str(err),
            )

        return records, raw_values
