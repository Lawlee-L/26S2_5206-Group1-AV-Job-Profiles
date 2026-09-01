from av_jobs.config import DEFAULT_CONFIG_PATH, load_sources


def test_in_scope_configuration_is_valid() -> None:
    sources = load_sources(DEFAULT_CONFIG_PATH)
    assert len(sources) == 27
    assert len({source.source_id for source in sources}) == len(sources)

