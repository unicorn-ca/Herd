import os
import yaml
import time
import string
from . import aws_interact

class logging:
    @staticmethod
    def log(*args, **kwargs):
        print(*args, **kwargs)

class MockDeployer():
    def __init__(self):
        pass


class Deployer():
    def __init__(self):
        # TODO load this from a config.py
        self._defaults = {
            'region': 'ap-southeast-1'
        }
        self._boto_handle    = None
        self._stack          = None
        self._cf_client      = None
        self._s3_client      = None
        self._synced         = []
        self._log_file       = None
        self._log_middleware = None

    def set_logger(self, output, middleware=lambda x,c:x):
        self._log_file = output
        self._log_middleware = middleware

    def log(self, message, priority=0):
        if self._log_file is None: return

        content = self._log_middleware(message, priority)
        if content is not None:
            self._log_file.write(content)

    def load_defaults(self, defaults={}):
        for cfg, val in defaults.items():
            self._defaults[cfg] = val

    def auth_boto(self, auth):
        self._boto_handle = aws_interact.Session()
        try:
            self._boto_handle.authenticate(auth)
        except:
            return None

        return self._boto_handle

    def make_cs_name(self):
        # Time based string generator
        charset = string.ascii_letters + string.digits
        def int_to_id(n):
            return (
                '0' if n == 0 else
                int_to_id(n // len(charset)).lstrip('0') + charset[n%len(charset)]
            )

        return int_to_id(int(time.time() * 10**6))

    def make_change_set(self, cs_args):
        def list_stacks(client):
            resp = client.list_stacks()
            while True:
                next_token = resp['NextToken'] if 'NextToken' in resp else None
                yield from (stack['StackName'] for stack in resp['StackSummaries'] if stack['StackStatus'] not in ['DELETE_IN_PROGRESS', 'DELETE_COMPLETE'])

                if next_token is None: break
                resp = client.list_stacks(NextToken=next_token)

        action = 'CREATE'
        for stack in list_stacks(self._cf_client):
            if cs_args['StackName'] == stack:
                action = 'UPDATE'
                break

        cs_args['ChangeSetType'] = action

        self.log(f'Making {action} change set', 1)
        cs = self._cf_client.create_change_set(**cs_args)
        try:
            self._cf_client.get_waiter('change_set_create_complete').wait(
                ChangeSetName=cs['Id'],
                WaiterConfig={'Delay': 10}
            )
        except boto3.botocore.exceptions.botocore.WaiterError:
            return None, action
        return cs, action

    def deploy_change_set(self, cs):
        cs_desc = self._cf_client.describe_change_set(ChangeSetName=cs['Id'])
        if cs_desc['ExecutionStatus'] != 'AVAILABLE':
            self.log('Change set is not in AVAILABLE state', 1)
            return {'StackId': cs_desc['StackId']}

        self.log('Deploying changeset', 2)
        self._cf_client.execute_change_set(ChangeSetName=cs['Id'])
        return {'StackId': cs_desc['StackId']}

    def deploy_stack(self, job, template_url=None):
        client = self._boto_handle.client('cloudformation', region=self._defaults['region'])
        self._cf_client = client

        changeset_name = self.make_cs_name()
        # TODO: adapt this to use create/execute changeset
        args = {
            'StackName': job['stack_name'] if 'stack_name' in job else job['name'],
            'Parameters': self.load_params(job['template_parameters'])
                            if 'template_parameters' in job else [],
            'Capabilities': job['capabilities'] if 'capabilities' in job else [],
            'Tags': job['tags'] if 'tags' in job else []
        }
        changeset_name = f'{args["StackName"]}-{changeset_name}-CS'
        args['ChangeSetName'] = changeset_name
        if template_url is None:
            args['TemplateBody'] = open(job['template_file']).read()
        else:
            args['TemplateURL'] = template_url

        self.log(f'Creating changeset [{changeset_name}]', 2)
        changeset, action = self.make_change_set(args)
        if changeset is None:
            self.log(f'Failed to create changeset [{changeset_name}]', 0)
            return {'StackId': None}

        return self.deploy_change_set(changeset), action

    def sync_files(self, sync):
        client = self._boto_handle.client('s3')
        self._s3_client = client

        keys = []
        for resource in sync['resources']:
            if sync['base_key'][-1] != '/':
                sync['base_key'] += '/'

            key = sync['base_key'] + os.path.basename(resource)
            keys.append(key)
            self.log(f'Uploading [{resource}] to [s3://{sync["bucket"] +"/"+ key}]', 2)
            client.upload_file(resource, sync['bucket'], key, ExtraArgs={'ACL':'aws-exec-read'})

        waiter = client.get_waiter('object_exists')
        for resource in keys:
            waiter.wait(Bucket=sync['bucket'], Key=resource)

        self._synced = keys
        return keys


    def hide_files(self, sync, keys):
        client = self._s3_client
        for resource in keys:
            client.put_object_acl(ACL='private', Bucket=sync['bucket'], Key=resource)


    def deploy(self, job):
        name = job['name']
        tpl_f = job['template_file']
        param_file = job['template_parameters'] if 'template_parameters' in job else None

        self.log(f'Deploying [{name}] from {tpl_f} using parameters {param_file}', 1)

        if self.auth_boto(job['authentication']) is None:
            self.log('Failed to authenticate', 0)
            return None
        else:
            self.log(f'Successfully authenticated', 1)

        tpl_url = None
        if 'sync' in job:
            uploaded = self.sync_files(job['sync'])
            self.log('Successfully uploaded all artifacts', 1)

            fsrc = tpl_f.split('://')
            if fsrc[0] == 'sync' and len(fsrc) == 2:
                loc = self._s3_client.get_bucket_location(Bucket=job['sync']['bucket'])['LocationConstraint']
                tpl_url = f"https://{job['sync']['bucket']}.s3-{loc}.amazonaws.com/{job['sync']['base_key']}{fsrc[1]}"

        self._stack, action = self.deploy_stack(job, tpl_url)
        self._stack = self._stack['StackId']
        if self._stack is None:
            self.log(f'Failed to deploy stack', 0)
            return None

        try:
            self.wait_for_completion(action.lower())
        except:
            self.log('Failed to execute deployment, check cloudformation for more details', 0);

        self.log(f'Finished deploying stack [{self._stack}]', 0)
        return self._stack

    def wait_for_completion(self, verb='create'):
        waiter = self._cf_client.get_waiter(f'stack_{verb}_complete')
        waiter.wait(StackName=self._stack, WaiterConfig={'Delay': 10, 'MaxAttempts': 360})

    def load_params(self, param_file):
        params = yaml.load(open(param_file), Loader=yaml.SafeLoader)

        if isinstance(params, list): return params

        if 'format' not in params:
            raise Exception('Formatted parameters must include a format')

        fmt = params['format']
        if fmt == 'aws':
            return params['params']
        elif fmt == 'key-value':
            ret = []
            for pname, pvalue in params['params'].items():
                ret.append({
                    'ParameterKey':   pname,
                    'ParameterValue': pvalue
                })
            return ret
        else:
            raise Exception(f'Unknown parameter format {fmt}')





