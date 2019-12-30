#!/usr/bin/python

# Copyright: (c) 2019, Confluent Inc

ANSIBLE_METADATA = {
    'metadata_version': '0.9',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: confluent_remove_deleted_connectors

short_description: This module removes the deleted connectors from a Connect cluster.

version_added: "2.4"

description:
    - "This module allows setting up Confluent connectors from Ansible."

options:
    connect_url:
        description:
            - URL of the Connect REST server to use to add/edit connectors
        required: true
    active_connectors:
        description:
            - List of names of active/current connectors 
        required: true

author:
    - Laurent Domenech-Cabaud (@ldom)
'''

EXAMPLES = '''
# Register a FileStreamSinkConnector
- connect_url: {{kafka_connect_http_protocol}}://0.0.0.0:{{kafka_connect_rest_port}}/connectors
  active_connectors: ["test-6-sink","test-5-sink"]
'''

RETURN = '''
message:
    description: The output message that the module generates
    type: str
    returned: always
'''

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url
import ansible.module_utils.six.moves.urllib.error as urllib_error


def get_current_connectors(connect_url):
    try:
        res = open_url(connect_url)
        return json.loads(res.read())
    except urllib_error.HTTPError as e:
        if e.code != 404:
            raise
        return []

def remove_connector(connect_url, name):
    url = "{}/{}".format(connect_url, name)
    r = open_url(method='DELETE', url=url)
    return r.getcode() == 200

def run_module():
    module_args = dict(
        connect_url=dict(type='str', required=True),
        active_connectors=dict(type='list', required=True),
    )

    result = dict(changed=False, message='')

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(**result)

    #
    # module action: makes a diff of existing (current) vs kept (active) connectors
    # and removes the un-kept ones
    #
    # note: using the logic below because PUT /connectors/<name>/config has proven to be unreliable
    # when the connector doesn't exist
    #
    try:
        current_connectors = set(get_current_connectors(connect_url=module.params['connect_url']))

        deleted_connectors = current_connectors - set(module.params['active_connectors'])

        for to_delete in deleted_connectors:
            remove_connector(connect_url=module.params['connect_url'], name=to_delete)

        result['changed'] = True
        result['message'] = "Connectors removed: {}.".format(', '.join(deleted_connectors))

    except Exception as e:
        result['changed'] = False
        result['message'] = str(e)
        module.fail_json(msg='An error occurred while running the module', **result)

    module.exit_json(**result)

def main():
    run_module()

if __name__ == '__main__':
    main()