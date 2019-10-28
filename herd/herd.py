import yaml
import deployment_interfaces as di

def run_deployments(cfg):
    deployer = di.Deployer()

    deployer.load_defaults(cfg['defaults'])
    for deployment in cfg['deployments']:
        deployer.deploy(deployment)

if __name__ == '__main__':
    import sys
    f = sys.argv[1]

    cfg = yaml.load(open(f), Loader=yaml.SafeLoader)
    run_deployments(cfg)
