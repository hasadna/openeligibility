import csv
import io
import itertools
from pathlib import Path
import yaml


def node_view(node):
    return (
        node['slug'],
        node['name']['source'] if isinstance(node['name'], dict) else node['name'],
        node['name']['tx']['he'] if isinstance(node['name'], dict) else None,
    )

def flatten(node, parent_node=None, grandparent_node=None):
    vals = []
    vals.append(node_view(node)[:1])
    vals.append(node_view(grandparent_node)[1:]) if grandparent_node else None, None
    vals.append(node_view(parent_node)[1:]) if parent_node else None, None
    vals.append(node_view(node)[1:])

    yield itertools.chain(*vals)
    if node.get('items'):
        for subnode in node.get('items'):
            yield from flatten(subnode, node, parent_node)


def write(filelike, filepath, headers=None):
    with io.open(Path(f'formats/{filepath}'), 'w') as servicesf:
        writer = csv.writer(servicesf)
        writer.writerow(headers) if headers else None
        writer.writerows(filelike)


def run():
    with io.open(Path('taxonomy.tx.yaml')) as f:
        services, situations = yaml.safe_load(f)

    write(flatten(services), 'services.csv', ('slug', 'g:name_en', 'g:name_he', 'p:name_en', 'p:name_he', 'name_en', 'name_he'))
    write(flatten(situations), 'situations.csv', ('slug', 'g:name_en', 'g:name_he', 'p:name_en', 'p:name_he', 'name_en', 'name_he'))


if __name__ == '__main__':
    run()
