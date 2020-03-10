import json

# noinspection PyUnresolvedReferences
from ansible.module_utils.six.moves.urllib.parse import urlencode
from ansible.module_utils.urls import open_url
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable

DOCUMENTATION = '''
    name: mackerel
    plugin_type: inventory
    author:
        - Tsuyoshi Maekawa <@xcezx>
    short_description: mackerel inventory source
    description:
        - Get inventory hosts from mackerel.io
        - Uses a YAML configuration file that ends with C(mackerel.(yml|yaml)).
    extends_documentation_fragment:
      - constructed
    options:
        plugin:
            description: Token that ensures this is a source file for the 'mackerel' plugin.
            required: True
            choices: ['mackerel']
        api_key:
            description: The API token for mackerel.io
            required: True
            type: string
            env:
              - name: MACKEREL_API_KEY
        query_filters:
            description:
              - A dictionary of find hosts query parameter value pairs.
              - Available filter are listed here U(https://mackerel.io/api-docs/entry/hosts#list).
            type: dict
            default: {}
'''

EXAMPLES = '''
# mackerel.yml file in YAML format
# Example command line: ansible-inventory --list -i mackerel.yml

plugin: mackerel
api_key: foobar
query_filters:
    service: my-service
    role: my-role # or [my-role]

compose:
    ansible_host: 'interfaces[0].ipAddress'
'''


class InventoryModule(BaseInventoryPlugin, Constructable):
    NAME = 'mackerel'

    def verify_file(self, path):
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(('mackerel.yml', 'mackerel.yaml')):
                return True
        return False

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        self._read_config_data(path)

        headers = {
            'X-Api-Key': self.get_option('api_key'),
            'Content-Type': 'application/json',
        }
        qs = urlencode(self.get_option('query_filters'), doseq=True)
        response = open_url('https://api.mackerelio.com/api/v0/hosts?' + qs, headers=headers)
        data = json.loads(response.read())

        group = self.inventory.add_group('mackerel')
        for host in data['hosts']:
            hostname = host.get('name')
            self.inventory.add_host(hostname, group=group)
            for attr, value in host.items():
                self.inventory.set_variable(hostname, attr, value)

            # Use constructed if applicable
            strict = self.get_option('strict')

            # Composed variables
            self._set_composite_vars(self.get_option('compose'), host, hostname, strict=strict)

            # Complex groups based on jinja2 conditionals, hosts that meet the conditional are added to group
            self._add_host_to_composed_groups(self.get_option('groups'), host, hostname, strict=strict)

            # Create groups based on variable values and add the corresponding hosts to it
            self._add_host_to_keyed_groups(self.get_option('keyed_groups'), host, hostname, strict=strict)
