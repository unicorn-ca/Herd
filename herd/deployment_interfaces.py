import os
import yaml
import aws_interact

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
        self._boto_handle = None
        self._stack       = None
        self._cf_client   = None
        self._s3_client   = None
        self._synced      = []

    def load_defaults(self, defaults={}):
        for cfg, val in defaults.items():
            self._defaults[cfg] = val

    def auth_boto(self, auth):
        self._boto_handle = aws_interact.Session()
        self._boto_handle.authenticate(auth)

        return self._boto_handle

    def deploy_stack(self, job, template_url=None):
        client = self._boto_handle.client('cloudformation', region=self._defaults['region'])
        self._cf_client = client

        args = {
            'StackName': job['stack_name'] if 'stack_name' in job else job['name'],
            'Parameters': yaml.load(open(job['template_parameters']), Loader=yaml.SafeLoader)
                            if 'template_parameters' in job else [],
            'DisableRollback': False,
            'TimeoutInMinutes': 100,
            'Capabilities': job['capabilities'] if 'capabilities' in job else [],
            'Tags': job['tags'] if 'tags' in job else []
        }
        if template_url is None:
            args['TemplateBody'] = open(job['template_file']).read()
        else:
            args['TemplateURL'] = template_url

        return client.create_stack(**args)

    def sync_files(self, sync):
        client = self._boto_handle.client('s3')
        self._s3_client = client

        keys = []
        for resource in sync['resources']:
            if sync['base_key'][-1] != '/':
                sync['base_key'] += '/'

            key = sync['base_key'] + os.path.basename(resource)
            keys.append(key)
            logging.log(f'Uploading [{resource}] to [s3://{sync["bucket"] +"/"+ key}]')
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

        logging.log(f'Deploying [{name}] from {tpl_f} using parameters {param_file}')

        self.auth_boto(job['authentication'])

        tpl_url = None
        if 'sync' in job:
            uploaded = self.sync_files(job['sync'])
            fsrc = tpl_f.split('://')
            if fsrc[0] == 'sync' and len(fsrc) == 2:
                loc = self._s3_client.get_bucket_location(Bucket=job['sync']['bucket'])['LocationConstraint']
                tpl_url = f"https://{job['sync']['bucket']}.s3-{loc}.amazonaws.com/{job['sync']['base_key']}{fsrc[1]}"

        self._stack = self.deploy_stack(job, tpl_url)['StackId']

        return self._stack

    def wait_for_completion(self):
        waiter = self._cf_client.get_waiter('stack_update_complete')
        waiter.wait(StackName=self._stack)
        
