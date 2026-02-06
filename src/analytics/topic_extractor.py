"""Topic extraction for categorizing user questions."""

import re
from typing import Optional
from enum import Enum


class Topic(str, Enum):
    """Topic categories for conversations."""
    ADOPTION = "adoption"
    ANIMALS = "animals"
    SERVICES = "services"
    HOURS_LOCATION = "hours_location"
    FEES = "fees"
    GENERAL = "general"


class TopicExtractor:
    """Extract topics from user messages using keyword matching."""

    # Adoption-related keywords
    ADOPTION_KEYWORDS = [
        "adopt", "adoption", "available", "find a pet", "looking for",
        "want to adopt", "adoptable", "adopting", "adopter", "adopte",
        "disponible", "cherche", "recherche", "adopter", "adoption"
    ]

    # Animal-related keywords (species, breeds, specific animals)
    ANIMAL_KEYWORDS = [
        "dog", "dogs", "puppy", "puppies", "cat", "cats", "kitten", "kittens",
        "rabbit", "rabbits", "bird", "birds", "pet", "pets", "animal", "animals",
        "breed", "breeds", "species", "chien", "chiens", "chiot", "chiots",
        "chat", "chats", "chaton", "chaton", "lapin", "lapins", "oiseau", "oiseaux",
        "animal", "animaux", "race", "races"
    ]

    # Services-related keywords
    SERVICES_KEYWORDS = [
        "veterinary", "vet", "clinic", "medical", "vaccination", "vaccine",
        "lost", "found", "surrender", "give up", "abandon", "stray",
        "emergency", "surgery", "spay", "neuter", "sterilize", "sterilization",
        "vétérinaire", "clinique", "perdu", "trouvé", "abandon", "abandonner",
        "urgence", "chirurgie", "stérilisation"
    ]

    # Hours and location keywords
    HOURS_LOCATION_KEYWORDS = [
        "hours", "open", "closed", "when", "time", "schedule", "location",
        "address", "directions", "where", "map", "visit", "come", "go",
        "heures", "ouvert", "fermé", "quand", "horaire", "adresse",
        "où", "carte", "visiter", "venir", "aller"
    ]

    # Fees-related keywords
    FEES_KEYWORDS = [
        "cost", "price", "fee", "fees", "charge", "charges", "how much",
        "payment", "pay", "costs", "pricing", "prix", "coût", "frais",
        "combien", "payer", "paiement"
    ]

    def __init__(self):
        # Compile regex patterns for case-insensitive matching
        self.adoption_pattern = re.compile(
            r'\b(' + '|'.join(self.ADOPTION_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.animal_pattern = re.compile(
            r'\b(' + '|'.join(self.ANIMAL_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.services_pattern = re.compile(
            r'\b(' + '|'.join(self.SERVICES_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.hours_location_pattern = re.compile(
            r'\b(' + '|'.join(self.HOURS_LOCATION_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.fees_pattern = re.compile(
            r'\b(' + '|'.join(self.FEES_KEYWORDS) + r')\b',
            re.IGNORECASE
        )

    def extract(self, message: str) -> Topic:
        """
        Extract topic from a message.
        
        Priority order (most specific first):
        1. Adoption (highest priority - most actionable)
        2. Fees (specific question type)
        3. Hours/Location (specific question type)
        4. Services (specific question type)
        5. Animals (general animal queries)
        6. General (fallback)
        """
        message_lower = message.lower()

        # Check in priority order
        if self.adoption_pattern.search(message_lower):
            return Topic.ADOPTION
        
        if self.fees_pattern.search(message_lower):
            return Topic.FEES
        
        if self.hours_location_pattern.search(message_lower):
            return Topic.HOURS_LOCATION
        
        if self.services_pattern.search(message_lower):
            return Topic.SERVICES
        
        if self.animal_pattern.search(message_lower):
            return Topic.ANIMALS
        
        return Topic.GENERAL

    def extract_all_topics(self, message: str) -> list[Topic]:
        """Extract all topics that match in a message (for multi-topic analysis)."""
        topics = []
        message_lower = message.lower()

        if self.adoption_pattern.search(message_lower):
            topics.append(Topic.ADOPTION)
        if self.fees_pattern.search(message_lower):
            topics.append(Topic.FEES)
        if self.hours_location_pattern.search(message_lower):
            topics.append(Topic.HOURS_LOCATION)
        if self.services_pattern.search(message_lower):
            topics.append(Topic.SERVICES)
        if self.animal_pattern.search(message_lower):
            topics.append(Topic.ANIMALS)

        # If no specific topics found, return GENERAL
        return topics if topics else [Topic.GENERAL]


# Global instance
_topic_extractor: Optional[TopicExtractor] = None


def get_topic_extractor() -> TopicExtractor:
    """Get the global topic extractor instance."""
    global _topic_extractor
    if _topic_extractor is None:
        _topic_extractor = TopicExtractor()
    return _topic_extractor


def extract_topic(message: str) -> Topic:
    """Convenience function to extract topic from a message."""
    return get_topic_extractor().extract(message)
