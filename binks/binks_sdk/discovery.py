# binks_sdk/discovery.py
"""ONVIF / WS-Discovery camera finder (LAN only, stdlib sockets).

Sends a WS-Discovery multicast Probe and collects XAddrs from replies.
Most IP cameras (and many "Brinks-style" / generic IoT cams) answer this.
Returns a list of dicts: {"xaddr": "...", "address": "..."}.

Nothing here authenticates or pulls video — it only finds devices so you
can add them with the right rtsp/snapshot URL.
"""
from __future__ import annotations
import socket
import uuid
import re

_MCAST = ("239.255.255.250", 3702)
_PROBE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
 xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
 xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
 xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
 <e:Header>
  <w:MessageID>uuid:{mid}</w:MessageID>
  <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
  <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
 </e:Header>
 <e:Body><d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe></e:Body>
</e:Envelope>"""


def discover_onvif(timeout: float = 3.0) -> list[dict]:
    msg = _PROBE.format(mid=uuid.uuid4()).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout)
    found: dict[str, dict] = {}
    try:
        sock.sendto(msg, _MCAST)
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                break
            text = data.decode("utf-8", "ignore")
            for x in re.findall(r"<[^>]*XAddrs>([^<]+)<", text):
                for url in x.split():
                    found[url] = {"xaddr": url, "address": addr[0]}
    except OSError:
        pass  # no multicast route (e.g. inside a container) — return empty
    finally:
        sock.close()
    return list(found.values())


if __name__ == "__main__":
    import json
    print(json.dumps(discover_onvif(), indent=2))
