from pathlib import Path
import yaml
import json
import requests
import os
from transifex.api import transifex_api


TRANSIFEX_TOKEN = os.environ.get('TRANSIFEX_TOKEN') or  os.environ.get('TX_TOKEN')
PROJECT = 'openeligibility'
ORGANIZATION = 'the-public-knowledge-workshop'

transifex_api.setup(auth=TRANSIFEX_TOKEN)

def transifex_slug(filename):
    return '_'.join(filename.parts).replace('.', '_')

def pull_translations(lang, filename):

    slug = transifex_slug(filename)

    organization = transifex_api.Organization.filter(slug=ORGANIZATION)[0]
    project = transifex_api.Project.filter(organization=organization, slug=PROJECT)[0]
    resource = transifex_api.Resource.filter(project=project, slug=slug)[0]
    language = transifex_api.Language.get(code=lang)
    url = transifex_api.ResourceTranslationsAsyncDownload.download(resource=resource, language=language)
    translations = requests.get(url).text
    translations = yaml.load(translations, Loader=yaml.SafeLoader)['en']

    ret = dict()
    for k, v in translations.items():
        if v:
            ret.setdefault(k, dict())[lang] = v.strip()
    return ret


def collect_keys(nodes, to_push, translated):
    for node in nodes:
        try:
            slug = node['slug']
            description_slug = slug + '::description'
            name = node['name']
        except Exception:
            print('Offending node:', node)
            raise
        to_push[slug] = name
        if slug in translated:
            node['name'] = dict(source=name, tx=translated[slug])
        description = node.get('description')
        if description:
            to_push[description_slug] = description
            if description_slug in translated:
                node['description'] = dict(source=description, tx=translated[description_slug])
        if 'items' in node:
            collect_keys(node['items'], to_push, translated)
    return to_push


if __name__ == '__main__':
    in_file = Path('taxonomy.yaml')
    translated = pull_translations('he', in_file)
    translations = yaml.load(in_file.open(), Loader=yaml.BaseLoader)
    to_push = collect_keys(translations, dict(), translated)
    json.dump(to_push, open('to_push.json', 'w'), indent=2)
    out_file = Path('taxonomy.tx.yaml')
    out_file.write_text(yaml.dump(translations, sort_keys=False, width=240, allow_unicode=True))