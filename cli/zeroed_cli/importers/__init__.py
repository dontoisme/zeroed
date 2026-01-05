"""
CSV importers for various bank formats.
"""

from pathlib import Path
from typing import Optional, List, Dict

from .base import BaseImporter
from .chase import ChaseImporter
from .generic import GenericImporter

# Registry of available importers
IMPORTERS = {
    "chase": ChaseImporter(),
    "generic": GenericImporter(),
}


def get_importer(format_name: str) -> BaseImporter:
    """Get importer by name."""
    if format_name not in IMPORTERS:
        available = ", ".join(IMPORTERS.keys())
        raise ValueError(f"Unknown format '{format_name}'. Available: {available}")
    return IMPORTERS[format_name]


def detect_format(filepath: Path) -> Optional[str]:
    """Auto-detect CSV format by examining the file."""
    for name, importer in IMPORTERS.items():
        if name == "generic":
            continue  # Skip generic as fallback
        if importer.detect(filepath):
            return name
    return None


def list_importers() -> List[Dict[str, str]]:
    """List all available importers."""
    return [
        {
            "name": name,
            "institution": importer.institution,
            "description": importer.description
        }
        for name, importer in IMPORTERS.items()
    ]
