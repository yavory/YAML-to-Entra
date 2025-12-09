import argparse
import sys
import logging
from .config import load_config
from .entra import EntraClient

def configure_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    parser = argparse.ArgumentParser(description="Provision Entra ID SAML Applications from YAML")
    parser.add_argument("config_file", help="Path to the YAML configuration file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    configure_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Loading configuration from {args.config_file}")
        config = load_config(args.config_file)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
        
    client = EntraClient()
    
    # load_config returns List[SAMLServiceProvider]
    for app_config in config:
        try:
            logger.info(f"Provisioning application: {app_config.metadata.name}")
            result = client.provision_app(app_config)
            logger.info(f"Successfully provisioned {app_config.metadata.name}: {result}")
        except Exception as e:
            logger.error(f"Error provisioning {app_config.metadata.name}: {e}")
            # Continue with next app or exit? Let's continue.

if __name__ == "__main__":
    main()
