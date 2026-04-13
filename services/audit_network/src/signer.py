"""KorPIX Audit Network — Record Signer (소프트웨어 구현 — UC-005에서 TPM 교체)"""
import hashlib


def sign_record(record_hash: str, terminal_id: str = "soft") -> str:
    """소프트 서명 — UC-005 하드웨어 전환 시 TPM AIK 서명으로 교체"""
    return hashlib.sha256(f"SOFT_SIG:{terminal_id}:{record_hash}".encode()).hexdigest()
