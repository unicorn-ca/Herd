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
        resources:
          - list of
          - resources
          - to upload
      template_file: /path/to/cfm/template.yaml    or    sync://basename_of_resource_in_sync.resources
      template_parameters: /path/to/parameters.yaml
      tags:
          - Key: tags
            Value: in a key, value format
```

## Parameters
The parameter file needs to be defined as either the standard aws format or the key-value pair format.

#### AWS format
The standard aws format spreads key-pairs into ParameterName, ParameterValue pairs. This can be supported either
by specifying `format: aws` into the document root:
```yaml
format: aws
params:
  - ParameterKey:   some-name
    ParameterValue: some-value
```

or by omitting the format/params fields altogether.
```yaml
- ParameterKey:   some-name
  ParameterValue: some-value
```

#### Key-Value format
The key-value format allows direct associatiton between keys and values.
```yaml
format: key-value
params:
    some-name: some-value
```

## TODO
 - More customization for deployments
 - Introduce dependancy model so we can parallelise deployments
 - Progress bar
 - Support middleware (compile troposphere to yaml then deploy that)
 - Support automatic deployments (work with tools that already have automatic deployment)
