"""Client MCP minimal pour l'editeur UE 5.8 (plugin ModelContextProtocol).

Transport : Streamable HTTP JSON-RPC sur http://127.0.0.1:8000/mcp, protocole 2025-06-18,
en-tete Mcp-Session-Id. Avec bEnableToolSearch=True le serveur n'expose que 3 meta-outils :
list_toolsets, describe_toolset, call_tool{toolset_name, tool_name (nom court), arguments}.
list_toolsets renvoie du texte '- <toolset>: <description>' ; les outils Python renvoient {'returnValue': ...}.

Usage Python :
    from mcp_client import McpClient
    with McpClient() as c:
        print(c.list_toolsets())
        print(c.call_tool('pj_tools.toolset.pj_tools', 'list_assets', {'path': '/Game/Carla'}))
        print(c.pj('list_assets', {'path': '/Game/Carla'}))          # raccourci

Usage CLI :
    python mcp_client.py wait [600]            attend que l'editeur reponde
    python mcp_client.py toolsets              liste des toolsets
    python mcp_client.py describe <toolset>    schema d'un toolset
    python mcp_client.py call <toolset> <outil> '<json arguments>'
    python mcp_client.py pj <outil> '<json arguments>'   raccourci vers le toolset pj_tools
"""
from __future__ import annotations

import itertools
import json
import re
import sys
import time

import requests

URL_DEFAUT = 'http://127.0.0.1:8000/mcp'
PROTOCOLE = '2025-06-18'


class McpErreur(RuntimeError):
    """Erreur JSON-RPC ou resultat isError=True."""


class McpClient:
    def __init__(self, url: str = URL_DEFAUT, timeout: float = 900.0, nom: str = 'claude-pj'):
        self.url = url
        self.timeout = timeout
        self.nom = nom
        self.session_id: str | None = None
        self._ids = itertools.count(1)
        self._http = requests.Session()
        self.info_serveur: dict = {}

    # -- transport -------------------------------------------------------
    def _entetes(self) -> dict:
        h = {'Content-Type': 'application/json',
             'Accept': 'application/json, text/event-stream',
             'MCP-Protocol-Version': PROTOCOLE}
        if self.session_id:
            h['Mcp-Session-Id'] = self.session_id
        return h

    @staticmethod
    def _decode(r: requests.Response):
        ct = r.headers.get('Content-Type', '')
        txt = r.content.decode('utf-8', 'replace')
        if not txt.strip():
            return None
        if 'text/event-stream' in ct:
            # derniere ligne data: contenant une reponse JSON-RPC
            dern = None
            for ligne in txt.splitlines():
                if ligne.startswith('data:'):
                    try:
                        obj = json.loads(ligne[5:].strip())
                    except ValueError:
                        continue
                    if isinstance(obj, dict) and ('result' in obj or 'error' in obj):
                        dern = obj
            return dern
        return json.loads(txt)

    def _post(self, corps: dict, timeout: float | None = None):
        r = self._http.post(self.url, data=json.dumps(corps), headers=self._entetes(),
                            timeout=timeout or self.timeout)
        sid = r.headers.get('Mcp-Session-Id')
        if sid:
            self.session_id = sid
        if r.status_code in (404, 400) and self.session_id and corps.get('method') != 'initialize':
            raise McpErreur(f'session invalide ({r.status_code}): {r.text[:300]}')
        r.raise_for_status()
        return self._decode(r)

    def rpc(self, methode: str, params: dict | None = None, timeout: float | None = None, _retry=True):
        corps = {'jsonrpc': '2.0', 'id': next(self._ids), 'method': methode}
        if params is not None:
            corps['params'] = params
        if self.session_id is None and methode != 'initialize':
            self.initialize()
        try:
            rep = self._post(corps, timeout)
        except McpErreur:
            if not _retry:
                raise
            self.session_id = None          # session expiree (editeur relance) : on rouvre
            self.initialize()
            return self.rpc(methode, params, timeout, _retry=False)
        if rep is None:
            return None
        if 'error' in rep:
            raise McpErreur(json.dumps(rep['error'], ensure_ascii=False))
        return rep.get('result')

    def notifier(self, methode: str, params: dict | None = None) -> None:
        corps = {'jsonrpc': '2.0', 'method': methode}
        if params is not None:
            corps['params'] = params
        r = self._http.post(self.url, data=json.dumps(corps), headers=self._entetes(), timeout=30)
        if r.status_code >= 400:
            raise McpErreur(f'notification {methode}: {r.status_code}')

    # -- cycle de vie -----------------------------------------------------
    def initialize(self, timeout: float = 30.0) -> dict:
        self.session_id = None
        corps = {'jsonrpc': '2.0', 'id': next(self._ids), 'method': 'initialize',
                 'params': {'protocolVersion': PROTOCOLE, 'capabilities': {},
                            'clientInfo': {'name': self.nom, 'version': '0.1'}}}
        rep = self._post(corps, timeout)
        if not rep or 'result' not in rep:
            raise McpErreur(f'initialize: reponse inattendue {rep!r}')
        self.info_serveur = rep['result']
        self.notifier('notifications/initialized')
        return self.info_serveur

    def fermer(self) -> None:
        if self.session_id:
            try:
                self._http.delete(self.url, headers={'Mcp-Session-Id': self.session_id}, timeout=10)
            except requests.RequestException:
                pass
        self.session_id = None

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, *exc):
        self.fermer()

    def attendre(self, max_s: float = 600.0, pas_s: float = 5.0) -> bool:
        """Sonde initialize jusqu'a reponse de l'editeur (True) ou expiration (False)."""
        t0 = time.time()
        while time.time() - t0 < max_s:
            try:
                self.initialize(timeout=10)
                return True
            except (requests.RequestException, McpErreur, ValueError):
                time.sleep(pas_s)
        return False

    # -- outils ------------------------------------------------------------
    def tools_list(self) -> list:
        return (self.rpc('tools/list', {}) or {}).get('tools', [])

    def appeler(self, nom: str, arguments: dict | None = None, timeout: float | None = None):
        """tools/call brut ; renvoie le texte (decode JSON si possible). Leve McpErreur si isError."""
        res = self.rpc('tools/call', {'name': nom, 'arguments': arguments or {}}, timeout)
        return self._contenu(res)

    @staticmethod
    def _contenu(res):
        if res is None:
            return None
        if 'structuredContent' in res and res['structuredContent'] is not None:
            val = res['structuredContent']
        else:
            textes = [c.get('text', '') for c in res.get('content', []) if c.get('type') == 'text']
            val = '\n'.join(textes)
            try:
                val = json.loads(val)
            except (ValueError, TypeError):
                pass
        if res.get('isError'):
            raise McpErreur(val if isinstance(val, str) else json.dumps(val, ensure_ascii=False))
        return val

    def list_toolsets(self):
        return self.appeler('list_toolsets', {})

    def describe_toolset(self, toolset_name: str):
        return self.appeler('describe_toolset', {'toolset_name': toolset_name})

    def call_tool(self, toolset_name: str, tool_name: str, arguments: dict | None = None,
                  timeout: float | None = None):
        """Appel d'un outil d'un toolset (via le meta-outil call_tool)."""
        val = self.appeler('call_tool', {'toolset_name': toolset_name, 'tool_name': tool_name,
                                         'arguments': arguments or {}}, timeout)
        # les outils pj_tools renvoient une chaine JSON : on la decode
        if isinstance(val, dict) and len(val) == 1 and next(iter(val)).lower() == 'returnvalue':
            val = next(iter(val.values()))
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except ValueError:
                pass
        return val

    def noms_toolsets(self) -> list[str]:
        """Noms complets des toolsets publies (ex. 'pj_tools.toolset.pj_tools')."""
        return _noms_toolsets(self.list_toolsets())

    def toolset_pj(self) -> str:
        """Nom complet du toolset pj_tools tel que publie par le registre."""
        if getattr(self, '_pj', None):
            return self._pj
        noms = self.noms_toolsets()
        for n in noms:
            if n.split('.')[-1].lower() == 'pj_tools':
                self._pj = n
                return n
        raise McpErreur(f'toolset pj_tools absent ; publies : {noms}')

    def pj(self, tool_name: str, arguments: dict | None = None, timeout: float | None = None):
        return self.call_tool(self.toolset_pj(), tool_name, arguments, timeout)


def _noms_toolsets(ts) -> list[str]:
    if isinstance(ts, dict):
        for cle in ('toolsets', 'Toolsets', 'result'):
            if cle in ts:
                return _noms_toolsets(ts[cle])
        return list(ts)
    if isinstance(ts, list):
        out = []
        for e in ts:
            if isinstance(e, str):
                out.append(e)
            elif isinstance(e, dict):
                out.append(e.get('name') or e.get('toolset_name') or e.get('Name') or json.dumps(e))
        return out
    if isinstance(ts, str):
        # format texte du serveur UE : "- <toolset>: <description>" (description sur plusieurs lignes)
        return re.findall(r'^- ([\w.]+):', ts, flags=re.M)
    return []


def _main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd, args = argv[0], argv[1:]
    c = McpClient()
    if cmd == 'wait':
        ok = c.attendre(float(args[0]) if args else 600.0)
        print('OK' if ok else 'TIMEOUT')
        return 0 if ok else 2
    try:
        c.initialize()
        if cmd == 'toolsets':
            out = c.list_toolsets()
        elif cmd == 'describe':
            out = c.describe_toolset(args[0])
        elif cmd == 'call':
            out = c.call_tool(args[0], args[1], json.loads(args[2]) if len(args) > 2 else {})
        elif cmd == 'pj':
            out = c.pj(args[0], json.loads(args[1]) if len(args) > 1 else {})
        elif cmd == 'tools':
            out = c.tools_list()
        else:
            print(__doc__)
            return 1
        print(out if isinstance(out, str) else json.dumps(out, indent=1, ensure_ascii=False))
        return 0
    finally:
        c.fermer()


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
