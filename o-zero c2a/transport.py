import json
import time
import websocket
import hashlib
from coincurve import PrivateKey

class OZeroNostrTransport:
    """
    Serverless transport wrapping the C2A protocol via valid NIP-01 Nostr events.
    """
    def __init__(self, relay_url="wss://relay.damus.io"):
        self.relay_url = relay_url
        
    def broadcast(self, signed_payload):
        try:
            # Generate ephemeral transport keypair for the relay
            privkey = PrivateKey()
            # Nostr requires the 32-byte X-coordinate for public keys
            pubkey = privkey.public_key.format(compressed=True)[1:].hex()
            
            created_at = int(time.time())
            kind = 30001
            tags = [["ozero", "c2a-intent"]]
            content = json.dumps(signed_payload)
            
            # NIP-01 Event ID: SHA256 of the strict JSON serialized array (no whitespaces)
            serialized = json.dumps([0, pubkey, created_at, kind, tags, content], separators=(',', ':'))
            event_id = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
            
            sig = privkey.sign_schnorr(bytes.fromhex(event_id)).hex()
            
            event_data = {
                "id": event_id,
                "pubkey": pubkey,
                "created_at": created_at,
                "kind": kind,
                "tags": tags,
                "content": content,
                "sig": sig
            }
                
            ws = websocket.WebSocket()
            ws.connect(self.relay_url)
            ws.send(json.dumps(["EVENT", event_data]))
            ws.close()
            return True
            
        except Exception as e:
            print(f"Transport error: {e}")
            return False