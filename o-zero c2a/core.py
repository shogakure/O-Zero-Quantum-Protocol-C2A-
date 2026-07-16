import json
import base64
import hashlib
import time
import uuid
# Note: Requires a compiled PQC library like 'dilithium-py'
from dilithium import Dilithium2

class OZeroConsumerIdentity:
    """
    Manages the ephemeral, quantum-resistant identity of a consumer.
    Keys should be generated per-session and never stored on disk.
    """
    @staticmethod
    def generate_ephemeral():
        public_key, private_key = Dilithium2.keygen()
        # Derive DID from SHA3-256 hash of the quantum public key bytes
        did_suffix = hashlib.sha3_256(public_key).hexdigest()[:40]
        
        return {
            "private_key": private_key,
            "public_key": public_key,
            "did": f"did:ozero:c2a:{did_suffix}"
        }

class OZeroC2AProtocol:
    """
    Strict, deterministic protocol ensuring quantum-secure intent payloads.
    """
    @staticmethod
    def _canonicalize(payload):
        """Forces strict, cross-language JSON formatting without whitespaces."""
        return json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')

    @staticmethod
    def create_intent(consumer_did, target_agent_id, action, parameters):
        """Creates a standardized payload with a cryptographic nonce and TTL."""
        return {
            "version": "2.0.0-quantum",
            "nonce": str(uuid.uuid4()), 
            "timestamp": int(time.time()),
            "consumer": consumer_did,
            "target_agent": target_agent_id,
            "action": action,
            "parameters": parameters
        }

    @classmethod
    def sign(cls, consumer_identity, intent):
        """Signs the canonical version of the intent with the quantum private key."""
        canonical_intent = cls._canonicalize(intent)
        signature = Dilithium2.sign(consumer_identity["private_key"], canonical_intent)
        return {
            "intent": intent,
            "signature": base64.b64encode(signature).decode('utf-8'),
            "public_key": base64.b64encode(consumer_identity["public_key"]).decode('utf-8')
        }

class OZeroAgentNode:
    """
    The Agent's receiver node. Ruthlessly validates quantum signatures, targets, and TTLs.
    """
    def __init__(self, agent_did, ttl_seconds=60):
        self.agent_did = agent_did
        self.ttl_seconds = ttl_seconds
        self.seen_nonces = {}

    def _cleanup_expired_nonces(self):
        """Memory protection: Removes nonces older than the allowed TTL window."""
        current_time = time.time()
        expired = [n for n, t in self.seen_nonces.items() if current_time - t > self.ttl_seconds]
        for n in expired:
            del self.seen_nonces[n]

    def verify(self, signed_payload):
        """Validates signature, anti-replay, and intended recipient."""
        self._cleanup_expired_nonces()
        
        intent = signed_payload.get("intent")
        signature_b64 = signed_payload.get("signature")
        pubkey_b64 = signed_payload.get("public_key")
        
        if not all([intent, signature_b64, pubkey_b64]):
            return {"status": "REJECTED", "reason": "Malformed payload structure."}

        # Target Validation
        if intent.get("target_agent") != self.agent_did:
            return {"status": "REJECTED", "reason": "Agent DID mismatch. Intent not addressed to this node."}
            
        nonce = intent.get("nonce")
        timestamp = intent.get("timestamp")
        
        # Symmetric Clock Protection
        if abs(time.time() - timestamp) > self.ttl_seconds:
            return {"status": "REJECTED", "reason": "TTL expired. Replay mitigation triggered."}
            
        # Memory-Safe Anti-Replay
        if nonce in self.seen_nonces:
            return {"status": "REJECTED", "reason": "Replay Attack Detected."}
            
        # Quantum Cryptographic Validation
        try:
            signature = base64.b64decode(signature_b64)
            public_key = base64.b64decode(pubkey_b64)
            canonical_intent = OZeroC2AProtocol._canonicalize(intent)
            
            is_valid = Dilithium2.verify(public_key, canonical_intent, signature)
            if not is_valid:
                return {"status": "REJECTED", "reason": "Quantum signature invalid."}
        except Exception as e:
            return {"status": "REJECTED", "reason": f"Verification error: {str(e)}"}
            
        # Register nonce
        self.seen_nonces[nonce] = time.time()
        tx_hash = hashlib.sha3_256(OZeroC2AProtocol._canonicalize(intent)).hexdigest()

        return {
            "status": "APPROVED",
            "transaction_hash": tx_hash,
            "message": "C2A interaction quantum-verified."
        }