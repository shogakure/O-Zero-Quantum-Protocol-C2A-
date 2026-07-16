import sys
import os

# Allow root module import when running as a standalone script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ozero_c2a.core import OZeroConsumerIdentity, OZeroC2AProtocol, OZeroAgentNode

# 1. Consumer Device: Generate Ephemeral Quantum Identity
print("--- 1. Generating Ephemeral Quantum Identity ---")
consumer = OZeroConsumerIdentity.generate_ephemeral()
print(f"Consumer DID: {consumer['did']}\n")

# 2. Consumer Device: Create and Sign Intent
print("--- 2. Creating C2A Intent ---")
TARGET_AGENT = "did:ozero:agent_alpha"

intent = OZeroC2AProtocol.create_intent(
    consumer_did=consumer["did"],
    target_agent_id=TARGET_AGENT,
    action="EXECUTE_TRANSACTION",
    parameters={"network": "mainnet", "amount": 500}
)

print("Signing with CRYSTALS-Dilithium...")
signed_payload = OZeroC2AProtocol.sign(consumer, intent)
print("Payload secured.\n")

# 3. Agent Node: Receive and Verify
print("--- 3. Agent Node Verifying Intent ---")
# Node initialized with the target DID to ensure it only accepts its own messages
agent_node = OZeroAgentNode(agent_did=TARGET_AGENT, ttl_seconds=30)
result = agent_node.verify(signed_payload)

print(f"Result Status: {result['status']}")
if result['status'] == "APPROVED":
    print(f"Tx Hash: {result['transaction_hash']}")
else:
    print(f"Reason: {result['reason']}")