"""Check published files/links/syntax; --refresh regenerates the file hash list."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'docs/publication-manifest.json'
EXCLUDED = {'.git', '__pycache__', '.venv', 'venv', 'runtime'}


def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file()
                  and not any(part in EXCLUDED for part in p.relative_to(ROOT).parts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    inventory = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in files() if p != MANIFEST}
    if args.refresh:
        MANIFEST.write_text(json.dumps(inventory, ensure_ascii=False, indent=2)+'\n')
    recorded = json.loads(MANIFEST.read_text())
    if inventory != recorded:
        raise ValueError('Publication manifest differs; inspect changes before --refresh')
    for p in files():
        rel = p.relative_to(ROOT)
        if any(part.startswith('workspace') for part in rel.parts) or p.suffix in {'.pt', '.pth', '.pyc', '.zip'} or p.name.startswith('.env'):
            raise ValueError(f'Unexpected runtime/private artifact: {rel}')
        if p.stat().st_size > 10_000_000:
            raise ValueError(f'Oversize file: {rel}')
        if p.suffix == '.py':
            ast.parse(p.read_text(), filename=str(rel))
        if p.suffix in {'.py', '.md', '.json', '.html', '.command', '.txt'}:
            text = p.read_text()
            if p != Path(__file__).resolve() and re.search(r'/Users/[^/\s]+/|10\.84\.\d+\.\d+|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}', text):
                raise ValueError(f'Personal path/address/credential pattern found: {rel}')
        if p.suffix == '.md':
            for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', p.read_text()):
                target = link.strip('<>').split('#')[0]
                if target and '://' not in target and not target.startswith('mailto:') and not (p.parent/target).exists():
                    raise ValueError(f'Broken link: {rel} -> {target}')
    print(f'OK: {len(inventory)} hashed files, Python syntax and Markdown links checked')


if __name__ == '__main__':
    main()
