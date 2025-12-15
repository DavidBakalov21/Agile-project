from typing import Dict, Any

class MemoryRepo:
    documents: Dict[str, Dict[str, Any]] = {}

    faqs: Dict[str, Dict[str, Any]] = {}
