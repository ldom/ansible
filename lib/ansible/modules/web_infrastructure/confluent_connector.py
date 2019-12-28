#!/usr/bin/python

# Copyright: (c) 2019, Confluent Inc

ANSIBLE_METADATA = {
    'metadata_version': '0.9',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: confluent_connector

short_description: This module allows setting up Confluent connectors from Ansible.

version_added: "2.4"

description:
    - "This module allows setting up Confluent connectors from Ansible."

options:
    connect_url:
        description:
            - URL of the Connect REST server to use to add/edit connectors
        required: true
    name:
        description:
            - Name of the connector
        required: true
    config:
        description:
            - JSON configuration of the connector
        required: true

author:
    - Laurent Domenech-Cabaud (@ldom)
'''

EXAMPLES = '''
# Register a FileStreamSinkConnector
- connect_url: {{kafka_connect_http_protocol}}://0.0.0.0:{{kafka_connect_rest_port}}/connectors
  name: local-file-sink
  config:
    connector.class: "FileStreamSinkConnector"
    tasks.max: 1
    file: "test.3.txt"
    topics: "test_laurent"
'''

RETURN = '''
message:
    description: The output message that the test module generates
    type: str
    returned: always
'''

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
import ansible.module_utils.six.moves.urllib.error as urllib_error


def connector_exists(connect_url, name):
    url = connect_url + '/' + name
    found = False
    try:
        open_url(url)
        found = True
    except urllib_error.HTTPError as e:
        if e.code != 404:
            raise
    return found

def install_new_connector(connect_url, name, config):
    data = json.dumps({'name': name, 'config': config})
    headers = {'Content-Type': 'application/json'}
    r = open_url(method='POST', url=connect_url, data=data, headers=headers)
    return r.status == 200 or r.status == 201

def update_existing_connector(connect_url, name, config):
    url = "{}/{}/config".format(connect_url, name)
    restart_url = "{}/{}/restart".format(connect_url, name)

    data = json.dumps(config)
    headers = {'Content-Type': 'application/json'}
    r = open_url(method='PUT', url=url, data=data, headers=headers)

    changed = r.status == 200 or r.status == 201

    r = open_url(method='POST', url=restart_url)
    if r.status not in (200, 204):
        raise Exception("Connector {} failed to restart after a configuration update. {}".format(name, r.msg))

    return changed

def run_module():
    module_args = dict(
        connect_url=dict(type='str', required=True),
        name=dict(type='str', required=True),
        config=dict(type='dict', required=True),
    )

    result = dict(changed=False, message='')

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(**result)

    #
    # module action: update the connector if it already exists, otherwise create a new one
    #
    # note: using the logic below because PUT /connectors/<name>/config has proven to be unreliable
    # when the connector doesn't exist
    #
    result['changed'] = False
    try:
        if connector_exists(
                connect_url=module.params['connect_url'],
                name=module.params['name']
        ):
            result['changed'] = update_existing_connector(
                connect_url=module.params['connect_url'],
                name=module.params['name'],
                config=module.params['config']
            )
            result['message'] = "Connector {} updated.".format(module.params['name'])
        else:
            result['changed'] = install_new_connector(
                connect_url=module.params['connect_url'],
                name=module.params['name'],
                config=module.params['config']
            )
            result['message'] = "New connector {} installed.".format(module.params['name'])
    except Exception as e:
        result['message'] = str(e)
        module.fail_json(msg='An error occurred while running the module', **result)

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()