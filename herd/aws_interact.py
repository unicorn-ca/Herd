import boto3

class Session:
    def __init__(self):
        self._session = None

    def authenticate(self, auth):
        args = {}
        if auth['type'] == 'profile':
            args['profile_name'] = auth['profile']
        elif auth['type'] == 'secret':
            args['aws_access_key_id'] = auth['access_key_id']
            args['aws_secret_access_key'] = auth['access_key']
        elif auth['type'] == 'token':
            args['aws_session_token'] = auth['token']
        else:
            raise Exception(f'Unknown authentication type {auth["type"]}')

        self._session = boto3.session.Session(**args)
        return self._session

    def client(self, resource, region=None):
        return self._session.client(resource, region_name=region)
