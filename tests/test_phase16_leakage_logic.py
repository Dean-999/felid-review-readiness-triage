from scripts.build_phase16_leakage_pressure_audit import path_site_proxy, same_proxy_group


def test_path_site_proxy_extracts_fcf_prefix():
    path = "/project/data/external/felidae_conservation_fund/images/bobcat_3000/69/2023-03/image.jpg"
    assert path_site_proxy(path) == "fcf:69:2023-03"


def test_path_site_proxy_extracts_czechlynx_collection_safely():
    path = "/project/data/raw/czechlynx/CzechLynx/foe_carpaths/lynx_248/14259_lynx_248.jpg"
    assert path_site_proxy(path) == "czechlynx:foe_carpaths"


def test_path_site_proxy_unknown_for_empty():
    assert path_site_proxy("") == "unknown"
    assert path_site_proxy(None) == "unknown"


def test_same_proxy_group():
    assert same_proxy_group("a", "a") is True
    assert same_proxy_group("a", "b") is False
    assert same_proxy_group("unknown", "unknown") is False
