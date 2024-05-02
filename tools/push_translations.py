from pathlib import Path
import yaml
import json
import os
from transifex.api import transifex_api


TRANSIFEX_TOKEN = os.environ.get('TRANSIFEX_TOKEN') or  os.environ.get('TX_TOKEN')
PROJECT = 'openeligibility'
ORGANIZATION = 'the-public-knowledge-workshop'

transifex_api.setup(auth=TRANSIFEX_TOKEN)

def transifex_slug(filename):
    return '_'.join(filename.parts).replace('.', '_')

def push_translations(filename: Path, translations):
    translations = dict(en=translations)
    content = yaml.dump(translations, allow_unicode=True, indent=2, width=1000000)
    slug = transifex_slug(filename)

    organization = transifex_api.Organization.filter(slug=ORGANIZATION)[0]
    project = transifex_api.Project.filter(organization=organization, slug=PROJECT)[0]
    resource = transifex_api.Resource.filter(project=project, slug=slug)
    YAML_GENERIC = transifex_api.i18n_formats.filter(organization=organization, name='YAML_GENERIC')[0]

    if len(resource) > 0:
        resource = resource[0]
        print('Update file:', resource, resource.attributes)
        ret = transifex_api.ResourceStringsAsyncUpload.upload(resource=resource, content=content)
        print('UPDATE', ret)

    else:
        print('New file:')
        resource = transifex_api.Resource.create(
            name=str(filename),
            slug=slug,
            accept_translations=True,
            i18n_format=YAML_GENERIC,
            project=project)
        ret = transifex_api.ResourceStringsAsyncUpload.upload(resource=resource, content=content)
        print('NEW', ret)


if __name__ == '__main__':
    to_push = json.load(open('to_push.json'))
    push_translations(Path('taxonomy.yaml'), to_push)
