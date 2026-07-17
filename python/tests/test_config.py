from masterytrace.core.config import DEFAULT_CONFIG, load_config


def test_returns_default_config_when_no_config_file_is_present(tmp_path):
    assert load_config(str(tmp_path)) == DEFAULT_CONFIG


def test_merges_an_on_disk_config_over_the_defaults(tmp_path):
    (tmp_path / "masterytrace.config.json").write_text('{"irt": {"iterations": 42}}', encoding="utf-8")
    config = load_config(str(tmp_path))
    assert config["irt"] == {"iterations": 42}
    assert config["bkt"] == DEFAULT_CONFIG["bkt"]
