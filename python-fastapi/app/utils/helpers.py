import re
import hashlib

def _norm_q(q: str) -> str:
    q = q.lower().strip()
    q = re.sub(r"\s+", " ", q)
    q = re.sub(r"[^\w\s]", "", q)
    return q

def _q_hash(q: str) -> str:
    return hashlib.sha256(_norm_q(q).encode("utf-8")).hexdigest()
