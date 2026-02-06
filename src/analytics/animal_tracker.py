"""Animal interest tracking - identify which animals are asked about most."""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AnimalReference:
    """Represents a reference to an animal in a message."""
    name: Optional[str] = None
    reference_number: Optional[str] = None
    species: Optional[str] = None


class AnimalTracker:
    """Track animal references in user messages."""

    # Pattern to match animal reference numbers (e.g., 200012345)
    REFERENCE_PATTERN = re.compile(r'\b(\d{10,})\b')

    # Common animal names (can be expanded)
    COMMON_ANIMAL_NAMES = [
        # Dogs
        "max", "bella", "charlie", "luna", "cooper", "daisy", "rocky", "milo",
        "sadie", "buddy", "molly", "bailey", "tucker", "lucy", "jack", "zoe",
        # Cats
        "whiskers", "fluffy", "shadow", "simba", "tiger", "mittens", "smokey",
        "ginger", "oreo", "pepper", "muffin", "coco", "princess", "sammy",
        # French names
        "max", "bella", "charlie", "luna", "cooper", "daisy", "rocky",
        "maxime", "belle", "charlotte", "lune", "cooper", "marguerite"
    ]

    def __init__(self):
        # Compile pattern for animal names (case-insensitive)
        self.name_pattern = re.compile(
            r'\b(' + '|'.join(self.COMMON_ANIMAL_NAMES) + r')\b',
            re.IGNORECASE
        )

    def extract_references(self, message: str) -> List[AnimalReference]:
        """
        Extract animal references from a message.
        
        Returns list of AnimalReference objects found in the message.
        """
        references = []
        message_lower = message.lower()

        # Look for reference numbers (10+ digits)
        ref_matches = self.REFERENCE_PATTERN.findall(message)
        for ref_num in ref_matches:
            # Reference numbers from SPCA are typically 10 digits starting with 2
            if ref_num.startswith('2') and len(ref_num) >= 10:
                references.append(AnimalReference(reference_number=ref_num))

        # Look for common animal names
        name_matches = self.name_pattern.findall(message_lower)
        for name in set(name_matches):  # Remove duplicates
            # Only add if we haven't already found this as a reference number
            if not any(ref.name == name for ref in references):
                references.append(AnimalReference(name=name))

        return references

    def extract_reference_number(self, message: str) -> Optional[str]:
        """Extract the first reference number found in a message."""
        ref_matches = self.REFERENCE_PATTERN.findall(message)
        for ref_num in ref_matches:
            if ref_num.startswith('2') and len(ref_num) >= 10:
                return ref_num
        return None

    def extract_animal_name(self, message: str) -> Optional[str]:
        """Extract the first animal name found in a message."""
        name_matches = self.name_pattern.findall(message.lower())
        if name_matches:
            return name_matches[0].capitalize()
        return None

    def has_animal_reference(self, message: str) -> bool:
        """Check if message contains any animal reference."""
        return len(self.extract_references(message)) > 0


# Global instance
_animal_tracker: Optional[AnimalTracker] = None


def get_animal_tracker() -> AnimalTracker:
    """Get the global animal tracker instance."""
    global _animal_tracker
    if _animal_tracker is None:
        _animal_tracker = AnimalTracker()
    return _animal_tracker


def extract_animal_references(message: str) -> List[AnimalReference]:
    """Convenience function to extract animal references from a message."""
    return get_animal_tracker().extract_references(message)
