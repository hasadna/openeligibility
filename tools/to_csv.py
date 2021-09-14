import csv
import io
from pathlib import Path
import yaml


def flatten(node):
    slug, name_en, name_he = (
        node['slug'],
        node['name']['source'] if isinstance(node['name'], dict) else node['name'],
        node['name']['tx']['he'] if isinstance(node['name'], dict) else None
    )

    yield (slug, name_en, name_he)
    if node.get('items'):
        for subnode in node.get('items'):
            yield from flatten(subnode)


def write(filelike, filepath, headers=None):
    with io.open(f'formats/{filepath}', 'w') as servicesf:
        writer = csv.writer(servicesf)
        writer.writerow(headers) if headers else None
        writer.writerows(filelike)


def run():
    with io.open('taxonomy.tx.yaml') as f:
        services, situations = yaml.safe_load(f)

    write(flatten(services), 'services.csv', ('slug', 'name_en', 'name_he'))
    write(flatten(situations), 'situations.csv', ())


if __name__ == '__main__':
    run()