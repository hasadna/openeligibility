import yaml
import csv
import io
from pathlib import Path

ROOT = Path(__file__).parent.parent
VERSIONS_DIR = ROOT / 'versions'
TAXONOMY_FILENAME = 'taxonomy.tx.yaml'
VERSION_FILENAME = 'VERSION'
CHANGELOG_FILENAME = 'CHANGELOG'
RENAMES_FILENAME = 'renames.txt'

def version_text_to_tuple(version_text):
    return tuple(map(int, version_text.strip().split('.')))

def version_tuple_to_text(version_tuple):
    return '.'.join(map(str, version_tuple))

def find_latest_version():
    # Find all directories under 'versions/' and find the latest version (by semantic versioning)
    versions = [d for d in VERSIONS_DIR.iterdir() if d.is_dir()]
    latest = max(versions, key=lambda x: version_text_to_tuple(x.name))
    return latest

def _read_taxonomy(items):
        for item in items:
            name = item.get('name')
            if isinstance(name, dict):
                name = name.get('tx', {}).get('he') or name.get('source')
            yield item['slug'], name
            if 'items' in item:
                yield from _read_taxonomy(item['items'])

def read_taxonomy(filepath):
    with open(filepath) as f:
        taxonomy = yaml.safe_load(f)
        return dict(_read_taxonomy(taxonomy))

if __name__ == '__main__':
    latest_dir = find_latest_version()
    latest_version = version_text_to_tuple(latest_dir.name)
    current_version = version_text_to_tuple((ROOT / VERSION_FILENAME).read_text().strip())
    latest_taxonomy = read_taxonomy(latest_dir / TAXONOMY_FILENAME)
    current_taxonomy = read_taxonomy(ROOT / TAXONOMY_FILENAME)

    print(f'Latest version: {latest_version}')
    print(f'Current version: {current_version}')

    added = set(current_taxonomy.keys()) - set(latest_taxonomy.keys())
    removed = set(latest_taxonomy.keys()) - set(current_taxonomy.keys())
    common = set(latest_taxonomy.keys()) & set(current_taxonomy.keys())
    changed = set(k for k in common if latest_taxonomy[k] != current_taxonomy[k])
    print(f'Added: {len(added)}')
    print(f'Removed: {len(removed)}')
    print(f'Changed: {len(changed)}')
    print(f'Unchanged: {len(common) - len(changed)}')

    renames_content = (VERSIONS_DIR / RENAMES_FILENAME).read_text().strip().split('\n')
    renames = []
    keep = []
    for line in renames_content:
        line = line.strip()
        if '->' in line and not line.startswith('#'):
            old, new = line.split('->')
            old = old.strip()
            new = new.strip()
            assert old in removed, f'Cannot rename {old} to {new} because {old} was not removed'
            assert new in added, f'Cannot rename {old} to {new} because {new} was not added'
            renames.append((old, new))
            removed.remove(old)
            added.remove(new)
        else:
            keep.append(line)

    if removed or renames:
        new_version = (latest_version[0] + 1, 0, 0)
    elif added:
        new_version = (latest_version[0], latest_version[1] + 1, 0)
    elif changed:
        new_version = (latest_version[0], latest_version[1], latest_version[2] + 1)
    else:
        new_version = latest_version

    latest_version = version_tuple_to_text(latest_version)
    new_version = version_tuple_to_text(new_version)
    current_version = version_tuple_to_text(current_version)

    print(f'Expected version: {new_version}')

    assert new_version == current_version, f'Version should be {new_version} but is {current_version}'
    if new_version == latest_version:
        print('No changes detected. Exiting.')
        exit(0)

    new_version_dir = VERSIONS_DIR / new_version
    new_version_dir.mkdir(exist_ok=True)

    report = []
    for slug in sorted(added):
        report.append(('added', slug))
    for slug in sorted(removed):
        report.append(('removed', slug))
    for slug in sorted(changed):
        report.append(('changed', slug))
    for old, new in sorted(renames):
        report.append(('renamed', old, new))
    
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerows(report)
    print(out.getvalue())

    (new_version_dir / CHANGELOG_FILENAME).write_text(out.getvalue())
    (new_version_dir / TAXONOMY_FILENAME).write_text((ROOT / TAXONOMY_FILENAME).read_text())
    (VERSIONS_DIR/ RENAMES_FILENAME).write_text('\n'.join(keep) + '\n')
