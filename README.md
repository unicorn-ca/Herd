# Herd

Herd is a tool to automate cross-account cloudformation deployments

## Usage
```sh
$ python3 herd.py path/to/config.yaml
```

## Configuration
Herd depends on a configuration file to define where resources should be deployed.
```yaml
defaults:
  region: region-to-deploy-into

deployments:
    - name: Name of the deployment
      stack_name: Name of the stack to deploy, defaults to name
      authentication:
        type: profile|secret|token
        profile: name of the cli profile to deploy from,     used by type=profile
        access_key_id: access key id of user to deploy with, used by type=secret
        access_key: access key of user to deploy with,       used by type=secret
        token: token to deploy with,                         used by type=token
      sync:
        bucket: bucket to upload to
        base_key: directory path to upload files to
        resources
          - list of
          - resources
          - to upload
      template_file: /path/to/cfm/template.yaml
      template_parameters: /path/to/parameters.yaml
      tags:
          - Key: tags
            Value: in a key, value format
```

## TODO
 - Automatically upload to s3 by default
 - More customization for deployments
 - Introduce dependancy model so we can parallelise deployments
 - Progress bar
 - Better parameter/tag format in the herd config
 - Support middleware (compile troposphere to yaml then deploy that)
 - Support automatic deployments (work with tools that already have automatic deployment)
