"""Terac collection-provider boundary."""

from forge.integrations.terac.client import TeracCampaignClient, TeracCampaignResult
from forge.integrations.terac.provider import TeracAssignment, TeracProvider

__all__ = [
    "TeracAssignment",
    "TeracCampaignClient",
    "TeracCampaignResult",
    "TeracProvider",
]
