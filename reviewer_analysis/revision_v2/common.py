"""Strict I/O, manifests, credential redaction and URL checks."""
from __future__ import annotations
import hashlib
import ipaddress
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(value).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding='utf-8-sig') as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try: obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f'{path}: invalid JSON on line {line_no}') from exc
                if not isinstance(obj, dict): raise ValueError(f'{path}:{line_no}: expected object')
                rows.append(obj)
    return rows


def write_json(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    os.replace(tmp, path)


def write_jsonl(path, rows):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf8') as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
    os.replace(tmp, path)


def new_directory(path):
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise ValueError(f'Output directory is not empty: {path}. Choose a new versioned directory.')
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_env(path=None):
    if path:
        from dotenv import load_dotenv
        if not Path(path).is_file(): raise ValueError('Environment file not found')
        load_dotenv(path, override=False)


def redact(text):
    text = str(text)
    for k, v in os.environ.items():
        if re.search(r'KEY|TOKEN|PASSWORD|SECRET', k, re.I) and not k.endswith('_KEY_ENV') and len(v) >= 4:
            text = text.replace(v, '[REDACTED]')
    return re.sub(r'(?i)(bearer\s+|sk-)[A-Za-z0-9_\-\.]{8,}', '[REDACTED]', text)


def validate_public_url(url):
    p = urlparse(str(url))
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Only HTTP(S) URLs without embedded credentials are allowed')
    host = p.hostname.lower().rstrip('.')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
        raise ValueError('Non-public target host')
    try:
        if not ipaddress.ip_address(host).is_global: raise ValueError('Non-public IP target')
    except ValueError as exc:
        if str(exc) == 'Non-public IP target': raise
        # Domain names are fetched only by the fixed Jina endpoint, never locally.
    if p.port not in (None,80,443): raise ValueError('Nonstandard target port')
    return str(url)


def qid(value):
    text = str(value)
    if text.upper().startswith('Q'): text = text[1:]
    if not text.isdigit(): raise ValueError(f'Invalid query ID: {value!r}')
    return f'Q{int(text)}'


def unique_index(rows, key):
    result = {}
    for row in rows:
        ident = row[key]
        if ident in result: raise ValueError(f'Duplicate {key}: {ident}')
        result[ident] = row
    return result
