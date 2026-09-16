from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from app.shared.domain.errors import InvalidDomainData


class KnowledgeNodeType(str, Enum):
    PROJECT = "project"
    DECISION = "decision"
    OPTION = "option"
    SCENARIO = "scenario"
    RISK = "risk"
    KPI = "kpi"
    KNOWLEDGE = "knowledge"
    ORGANIZATION = "organization"
    PERSON = "person"
    CONCEPT = "concept"


class KnowledgeRelationType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"
    RELATES_TO = "relates_to"
    DERIVED_FROM = "derived_from"
    MEASURES = "measures"
    AFFECTS = "affects"
    MITIGATES = "mitigates"
    BELONGS_TO = "belongs_to"


@dataclass(frozen=True)
class KnowledgeNode:
    id: UUID
    tenant_id: UUID
    node_type: KnowledgeNodeType
    label: str
    source: str
    source_uri: str | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id,
        node_type,
        label,
        source,
        source_uri=None,
    ):
        if not isinstance(tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")

        try:
            node_type = KnowledgeNodeType(node_type)
        except (TypeError, ValueError) as exc:
            raise InvalidDomainData("invalid knowledge node type") from exc

        if not isinstance(label, str) or not label.strip():
            raise InvalidDomainData("node label is required")

        if not isinstance(source, str) or not source.strip():
            raise InvalidDomainData("node source is required")

        if source_uri is not None and (
            not isinstance(source_uri, str) or not source_uri.strip()
        ):
            raise InvalidDomainData("source_uri must be a non-empty string")

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            node_type=node_type,
            label=label.strip(),
            source=source.strip(),
            source_uri=source_uri.strip() if source_uri else None,
            created_at=datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class KnowledgeEdge:
    id: UUID
    tenant_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    relation_type: KnowledgeRelationType
    source: str
    confidence: float | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id,
        source_node_id,
        target_node_id,
        relation_type,
        source,
        confidence=None,
    ):
        if not isinstance(tenant_id, UUID):
            raise InvalidDomainData("tenant_id must be UUID")

        if not isinstance(source_node_id, UUID):
            raise InvalidDomainData("source_node_id must be UUID")

        if not isinstance(target_node_id, UUID):
            raise InvalidDomainData("target_node_id must be UUID")

        if source_node_id == target_node_id:
            raise InvalidDomainData("self-referencing edge is not allowed")

        try:
            relation_type = KnowledgeRelationType(relation_type)
        except (TypeError, ValueError) as exc:
            raise InvalidDomainData("invalid knowledge relation type") from exc

        if not isinstance(source, str) or not source.strip():
            raise InvalidDomainData("edge source is required")

        if confidence is not None:
            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= float(confidence) <= 1
            ):
                raise InvalidDomainData(
                    "confidence must be numeric between 0 and 1"
                )
            confidence = float(confidence)

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            source=source.strip(),
            confidence=confidence,
            created_at=datetime.now(timezone.utc),
        )
