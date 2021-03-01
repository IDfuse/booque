import pathlib
from xdg import xdg_config_home
import click
import json

field_map = {
        'TITLE': "description.title",
        'ABS': "description.abstract",
        'KEY': "description.keywords",
    }

class PlPath(click.Path):
    """A Click path argument that returns a pathlib Path, not a string"""
    def convert(self, value, param, ctx):
        return pathlib.Path(super().convert(value, param, ctx))


def add_highlight(query):
    query['highlight'] = {
            'pre_tags': [ "HLSHL" ],
            'post_tags': [ "HLEHL" ],
            'fields': { '*': {} },
            'fragment_size': 2147483647,
        }

def read_config():
    f = xdg_config_home() / "booque" / "config.json"
    if f.exists():
        with f.open(mode="r") as fh:
            config = json.load(fh)
            field_map.update(config['fields'])
    else:
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open(mode="w") as fh:
            json.dump({'fields': field_map}, fh, indent=4)

