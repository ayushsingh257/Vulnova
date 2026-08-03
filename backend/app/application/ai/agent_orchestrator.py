"""Multi-Agent Intent Router & Prompt Orchestrator for AI Security Copilot."""

from typing import Optional
from uuid import UUID

from app.domain.entities.ai import CopilotAgentType


class AgentOrchestrator:
    """Orchestrator classifying user query intent and routing to specialized sub-agent personas."""

    @staticmethod
    def classify_intent(
        query_text: str, context_finding_id: Optional[UUID] = None
    ) -> CopilotAgentType:
        """Analyze analyst query string and classify intended sub-agent persona."""
        lower_q = query_text.lower()

        if any(
            w in lower_q
            for w in ["explain", "cvss", "epss", "what is", "why is this", "impact"]
        ):
            return CopilotAgentType.EXPLAINER

        if any(
            w in lower_q
            for w in [
                "attack path",
                "kill chain",
                "mitre",
                "lateral movement",
                "exploit path",
                "journey",
            ]
        ):
            return CopilotAgentType.ATTACK_PATH

        if any(
            w in lower_q
            for w in [
                "remediate",
                "fix",
                "patch",
                "code snippet",
                "mitigation",
                "how to fix",
            ]
        ):
            return CopilotAgentType.REMEDIATION

        if any(
            w in lower_q
            for w in [
                "false positive",
                "confidence",
                "duplicate",
                "accuracy",
                "true positive",
                "noise",
            ]
        ):
            return CopilotAgentType.FALSE_POSITIVE

        if any(
            w in lower_q
            for w in [
                "owasp",
                "cwe",
                "capec",
                "policy",
                "standard",
                "guideline",
                "search knowledge",
                "compliance",
            ]
        ):
            return CopilotAgentType.KNOWLEDGE_RAG

        return CopilotAgentType.SECURITY_ANALYST

    @staticmethod
    def build_system_prompt(
        agent_type: CopilotAgentType,
        rag_context_block: Optional[str] = None,
        investigation_state_summary: Optional[str] = None,
    ) -> str:
        """Construct sub-agent persona prompt instructions."""
        base_prompt = (
            "You are Vulnova Security Copilot, an enterprise-grade AI SOC analyst assistant.\n"
            "Safety Requirement: You operate under a strict READ-ONLY Human-in-the-Loop policy.\n"
            "You can analyze findings, explain technical details, synthesize attack paths, recommend remediations, "
            "and search security standards. You CANNOT execute system commands, modify production servers, or close findings.\n"
        )

        agent_instructions = {
            CopilotAgentType.SECURITY_ANALYST: (
                "Role: Lead Security Analyst.\n"
                "Task: Provide comprehensive security posture analysis, finding investigation summaries, and strategic advice.\n"
            ),
            CopilotAgentType.EXPLAINER: (
                "Role: Vulnerability Explanation Specialist.\n"
                "Task: Explain root causes, vulnerability categories, technical mechanics, CVSS/EPSS factors, and asset business impact.\n"
            ),
            CopilotAgentType.ATTACK_PATH: (
                "Role: Threat Intelligence & Attack Path Specialist.\n"
                "Task: Detail attacker journey progressions, entry vectors, MITRE ATT&CK techniques, and lateral movement risks.\n"
            ),
            CopilotAgentType.REMEDIATION: (
                "Role: Security Remediation Engineer.\n"
                "Task: Provide multi-tier fix recommendations, safe code patch diff suggestions, configuration updates, and rollback steps.\n"
            ),
            CopilotAgentType.FALSE_POSITIVE: (
                "Role: Finding Authenticity & Detection Analyst.\n"
                "Task: Evaluate finding confidence levels, evidence quality scores, supporting/contradicting proofs, and duplicate similarity.\n"
            ),
            CopilotAgentType.KNOWLEDGE_RAG: (
                "Role: Security Knowledge & Standards Librarian.\n"
                "Task: Retrieve and cite OWASP Cheat Sheets, CWE definitions, CAPEC attack patterns, NVD data, and internal policies.\n"
            ),
        }

        full_prompt = base_prompt + agent_instructions.get(agent_type, "")

        if investigation_state_summary:
            full_prompt += f"\n<investigation_state>\n{investigation_state_summary}\n</investigation_state>\n"

        if rag_context_block:
            full_prompt += f"\n{rag_context_block}\n"

        return full_prompt
