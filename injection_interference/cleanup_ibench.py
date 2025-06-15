import argparse
from kubernetes import client, config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--namespace', default='default')
    parser.add_argument('--nginx', action='store_true')
    args = parser.parse_args()

    config.load_kube_config()
    apps = client.AppsV1Api()
    
    name = "ibench-cpu-nginx" if args.nginx else "ibench-cpu"

    try:
        apps.delete_namespaced_deployment(
            name=name,
            namespace=args.namespace,
            body=client.V1DeleteOptions()
        )
        print(f"Deleted {name}")
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == '__main__':
    main()