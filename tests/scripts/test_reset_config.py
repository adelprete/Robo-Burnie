import json

from robo_burnie.scripts.reset_config import _main


def test_reset_config_exists(tmpdir):
    config_path = tmpdir.join(".config.json")
    with open(config_path, "w") as config:
        json.dump(
            {"scripts": {"reset_config": {"enabled": True, "default_enabled": False}}},
            config,
        )

    _main(config_path.strpath)

    config = json.load(config_path)
    assert config == {
        "scripts": {"reset_config": {"enabled": False, "default_enabled": False}}
    }


def test_reset_config_doesnt_exist(tmpdir):
    config_path = tmpdir.join(".new_config.json")

    _main(config_path.strpath)

    config = json.load(config_path)
    with open("src/robo_burnie/default_config.json", "r") as default_config:
        default_config = json.load(default_config)
    assert config == default_config
