import yaml
import csv
import io
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).parent.parent
VERSIONS_DIR = ROOT / 'versions'
TAXONOMY_FILENAME = 'taxonomy.tx.yaml'
VERSION_FILENAME = 'VERSION'
CHANGELOG_FILENAME = 'CHANGELOG'
RENAMES_FILENAME = 'renames.txt'
IDS_FILENAME = VERSIONS_DIR / 'PRIMARY_KEYS'

def version_text_to_tuple(version_text):
    return tuple(map(int, version_text.strip().split('.')))

def version_tuple_to_text(version_tuple):
    return '.'.join(map(str, version_tuple))

def find_latest_version():
    # Find all directories under 'versions/' and find the latest version (by semantic versioning)
    versions = [d for d in VERSIONS_DIR.iterdir() if d.is_dir()]
    latest = max(versions, key=lambda x: version_text_to_tuple(x.name))
    return latest

def _read_taxonomy(items, slug_to_pk):
    for item in items:
        name = item.get('name')
        if isinstance(name, dict):
            en_name = name.get('source')
            he_name = name.get('tx', {}).get('he') or en_name
        else:
            en_name = name
            he_name = None
        pk = item.get('pk')
        if pk is None:
            pk = slug_to_pk.get(item['slug'])
            if pk is None:
                pk = uuid4().hex
                slug_to_pk[item['slug']] = pk
            item['pk'] = pk
        yield pk, (item['slug'], en_name, he_name)
        if 'items' in item:
            yield from _read_taxonomy(item['items'], slug_to_pk)

def read_taxonomy(filepath, slug_to_pk=None):
    with open(filepath) as f:
        taxonomy = yaml.safe_load(f)
        ret = dict(_read_taxonomy(taxonomy, slug_to_pk))
        return ret, taxonomy

def read_renames(slug_to_pk):
    renames_content = (VERSIONS_DIR / RENAMES_FILENAME).read_text().strip().split('\n')
    renames = []
    keep = []
    for line in renames_content:
        line = line.strip()
        if '->' in line and not line.startswith('#'):
            old, new = line.split('->')
            old = old.strip()
            new = new.strip()
            renames.append((old, new))
        else:
            keep.append(line)
    for old, new in renames:
        slug_to_pk[new] = slug_to_pk[old]    
    return keep, renames

def read_pks():
    slug_to_pk = {}
    try:
        with open(IDS_FILENAME) as f:
            for line in f:
                pk, slug = line.strip().split(',')
                slug_to_pk[slug] = pk
    except FileNotFoundError:
        pass
    return slug_to_pk

def write_pks(slug_to_pk, renames):
    old_slugs = set(old for old, _ in renames)
    items = sorted(slug_to_pk.items())
    items = [(slug, pk) for slug, pk in items if slug not in old_slugs]
    with open(IDS_FILENAME, 'w') as f:
        for slug, pk in items:
            f.write(f'{pk},{slug}\n')

if __name__ == '__main__':
    latest_dir = find_latest_version()
    latest_version = version_text_to_tuple(latest_dir.name)
    current_version = version_text_to_tuple((ROOT / VERSION_FILENAME).read_text().strip())
    slug_to_pk = read_pks()
    latest_taxonomy, _ = read_taxonomy(latest_dir / TAXONOMY_FILENAME, slug_to_pk)
    keep, renames = read_renames(slug_to_pk)
    current_taxonomy, current_taxonomy_orig = read_taxonomy(ROOT / TAXONOMY_FILENAME, slug_to_pk)

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

    if removed:
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
    for pk in sorted(added):
        report.append(('added', pk, current_taxonomy[pk][0], current_taxonomy[pk][1], current_taxonomy[pk][2]))
    for pk in sorted(removed):
        report.append(('removed', pk))
    for pk in sorted(changed):
        report.append(('changed', pk, current_taxonomy[pk][0], current_taxonomy[pk][1], current_taxonomy[pk][2]))
    
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerows(report)
    print(out.getvalue())

    (new_version_dir / CHANGELOG_FILENAME).write_text(out.getvalue())
    with (new_version_dir / TAXONOMY_FILENAME).open('w') as f:        
        yaml.dump(current_taxonomy_orig, f, sort_keys=False, width=240, allow_unicode=True)
    with (ROOT / TAXONOMY_FILENAME).open('w') as f:
        yaml.dump(current_taxonomy_orig, f, sort_keys=False, width=240, allow_unicode=True)
    (VERSIONS_DIR/ RENAMES_FILENAME).write_text('\n'.join(keep) + '\n')
    write_pks(slug_to_pk, renames)
