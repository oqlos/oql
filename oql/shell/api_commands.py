"""API command handlers: API, CREATE_PROTOCOL."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict


class ApiCommandsMixin:
    """Commands that make HTTP calls to the backend API."""

    async def cmd_api(self, args: str) -> Dict:
        """API GET|POST|PUT|DELETE "url" {...} """
        parts = args.strip().split(None, 2)
        if len(parts) < 2:
            print("❌ Usage: API GET|POST|PUT|DELETE \"url\" {...}")
            return {}

        method = parts[0].upper()
        url = parts[1].strip('"\'')
        data = {}
        if len(parts) > 2 and parts[2].startswith('{'):
            try:
                data = json.loads(parts[2])
            except Exception:
                pass

        if url.startswith('/'):
            url = f"{self.api_url}{url}"

        try:
            req_data = json.dumps(data).encode('utf-8') if data else None
            req = urllib.request.Request(
                url,
                data=req_data,
                method=method,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                result_text = resp.read().decode('utf-8')
                try:
                    result = json.loads(result_text)
                except Exception:
                    result = {"text": result_text[:200]}

                icon = "✅" if status < 400 else "❌"
                print(f"{icon} API {method} {url} → {status}")

                event = await self.emit_event("api.response", {
                    "method": method,
                    "url": url,
                    "status": status,
                    "data": result
                })
                return event
        except urllib.error.HTTPError as e:
            print(f"❌ API {method} {url} → {e.code}")
            return {}
        except Exception as e:
            print(f"❌ API Error: {e}")
            return {}

    async def cmd_create_protocol(self, args: str) -> Dict:
        """CREATE_PROTOCOL "name" {...} - Create protocol via API"""
        parts = self._parse_target_and_json(args)
        name = parts[0]
        data = parts[1]

        payload = {
            "name": name,
            "device_id": data.get("device_id", "d-test-001"),
            "status": data.get("status", "COMPLETED"),
            "test_date": data.get("test_date", datetime.now(timezone.utc).isoformat()),
            "results": data.get("results", {"passed": True}),
            **{k: v for k, v in data.items() if k not in ["device_id", "status", "test_date", "results"]}
        }

        try:
            req = urllib.request.Request(
                f"{self.api_url}/api/v3/data/protocols",
                data=json.dumps(payload).encode('utf-8'),
                method='POST',
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                result_text = resp.read().decode('utf-8')
                try:
                    result = json.loads(result_text)
                except Exception:
                    result = {}

                if status < 400:
                    protocol_id = result.get('id') or result.get('data', {}).get('id', 'unknown')
                    print(f"✅ CREATE_PROTOCOL {name} → {protocol_id}")
                    event = await self.emit_event("protocol.created", {
                        "protocolId": protocol_id,
                        "name": name,
                        **payload
                    })
                    return event
                else:
                    print(f"❌ CREATE_PROTOCOL failed: {status}")
                    return {}
        except urllib.error.HTTPError as e:
            print(f"❌ CREATE_PROTOCOL failed: {e.code}")
            return {}
        except Exception as e:
            print(f"❌ CREATE_PROTOCOL Error: {e}")
            return {}
