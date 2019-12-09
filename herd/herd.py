import sys
import yaml
from . import deployment_interfaces as di

def run_deployments(cfg):
    for deployment in cfg['deployments']:
        deployer = di.Deployer()
        deployer.set_logger(sys.stdout, lambda m,p: f'[{p}] {m}\n')
        deployer.load_defaults(cfg['defaults'])
        stack_id = deployer.deploy(deployment)

if __name__ == '__main__':
    import sys
    f = sys.argv[1]

    cfg = yaml.load(open(f), Loader=yaml.SafeLoader)
    run_deployments(cfg)
