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

    def load_defaults(self, defaults={}):
        for cfg, val in defaults.items():
            self._defaults[cfg] = val

    def deploy(self, job):
        name = job['name']
        template_file = job['template_file']
        param_file = job['template_parameters'] if 'template_parameters' in job else None

        logging.log(f'Deploying [{name}] from {template_file} using parameters {param_file}')

        awsi = aws_interact.Session()
        awsi.authenticate(job['authentication'])

        # TODO: copy to s3 by default
        client = awsi.client('cloudformation', region=self._defaults['region'])
        stackid = client.create_stack(
            StackName=job['stack_name'] if 'stack_name' in job else job['name'],
            TemplateBody=open(template_file).read(),
            Parameters=yaml.load(open(param_file), Loader=yaml.SafeLoader) if param_file is not None else [],
            DisableRollback=False,
            TimeoutInMinutes=100,
            Capabilities=job['capabilities'] if 'capabilities' in job else [],
            # TODO: support {k:v} style tags
            Tags=job['tags'] if 'tags' in job else []
        )

        return stackid['StackId']  # TODO: handle failure

        
