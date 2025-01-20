import json
import logging

from robo_burnie import _helpers

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
)

CONFIG_PATH = "src/robo_burnie/.config.json"


def _main(config_path: str) -> None:
    """Resets the config file to the default values and creates a config file if one doesnt exist."""
    with open("src/robo_burnie/default_config.json", "r") as default_config:
        default_config = json.load(default_config)

    try:
        with open(config_path, "r+") as config_file:
            config_dict = json.load(config_file)
            for _, values in config_dict["scripts"].items():
                values["enabled"] = values["default_enabled"]
            config_file.seek(0)
            json.dump(config_dict, config_file, indent=4)
            config_file.truncate()
    except FileNotFoundError:
        # Creating the .config file for the first time because it doesnt exist
        with open(config_path, "w") as config:
            json.dump(default_config, config, indent=4)
    logger.info("Config file reset to default values")


if __name__ == "__main__":
    if _helpers.is_script_enabled("reset_config"):
        _main(CONFIG_PATH)
    else:
        logger.debug("reset_config is disabled")
