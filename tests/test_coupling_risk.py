"""Directive §5 B2 — per-class soft coupling-site-availability flag (THINK T15)."""

from eps.properties.coupling_risk import coupling_risk_flag


def test_alpha_diblocked_pyrrole_flagged():
    # 2,5-dimethylpyrrole: both alpha blocked -> risk (the clean intrinsic-NO catch)
    r = coupling_risk_flag("Cc1ccc(C)[nH]1", "alpha")
    assert r["coupling_risk"] == "risk_alpha_blocked"
    assert r["n_free_alpha"] == 0


def test_one_free_alpha_not_flagged():
    # 2-methylfuran (YES): one free alpha still couples -> ok at default min_free_alpha=1
    r = coupling_risk_flag("Cc1ccco1", "alpha")
    assert r["coupling_risk"] == "ok"
    assert r["n_free_alpha"] == 1


def test_simple_thiophene_ok():
    assert coupling_risk_flag("c1ccsc1", "alpha")["coupling_risk"] == "ok"


def test_min_free_alpha_is_config_driven():
    # raising the threshold to 2 flags the one-free-alpha case (proves threshold is not hardcoded)
    assert coupling_risk_flag("Cc1ccco1", "alpha", min_free_alpha=2)["coupling_risk"] == "risk_alpha_blocked"


def test_carbazole_3_6_blocked_alkyl_and_aryl():
    # 3,6-di-tert-butyl (alkyl) and 3,6-diphenyl (aryl) carbazoles: both 3,6 blocked -> risk
    assert coupling_risk_flag("CC(C)(C)c1ccc2[nH]c3ccc(C(C)(C)C)cc3c2c1", "alpha")["coupling_risk"] == "risk_3_6_blocked"
    assert coupling_risk_flag("c1ccc(-c2ccc3[nH]c4ccc(-c5ccccc5)cc4c3c2)cc1", "alpha")["coupling_risk"] == "risk_3_6_blocked"


def test_carbazole_with_free_site_ok():
    # parent carbazole (3,6 free) and 3-ethylcarbazole (3 sub / 6 free) -> ok (>=1 free coupling site)
    assert coupling_risk_flag("c1ccc2c(c1)[nH]c1ccccc12", "alpha")["coupling_risk"] == "ok"
    assert coupling_risk_flag("CCc1ccc2[nH]c3ccccc3c2c1", "alpha")["coupling_risk"] == "ok"
    # N-phenylcarbazole: 3,6 free (its NO is a 3,3'-dimerization blind spot, not a site block)
    assert coupling_risk_flag("c1ccc(-n2c3ccccc3c3ccccc32)cc1", "alpha")["coupling_risk"] == "ok"


def test_electronic_and_beta_steric_NOs_are_blind_spots():
    # 3-thiophenecarboxaldehyde (electronic) and 3,4-dibutylthiophene (beta-steric): alpha free ->
    # NOT flagged. Documented screening-grade blind spots (B1) — the flag must not claim to catch them.
    assert coupling_risk_flag("O=Cc1ccsc1", "alpha")["coupling_risk"] == "ok"
    assert coupling_risk_flag("CCCCc1cscc1CCCC", "alpha")["coupling_risk"] == "ok"


def test_explicit_nonring_class_not_assessed():
    # diphenylamine-type explicit coupler: screening-grade not assessable -> honest 'not_assessed'
    assert coupling_risk_flag("c1ccc(Nc2ccccc2)cc1", "explicit")["coupling_risk"] == "not_assessed"


def test_unparseable():
    assert coupling_risk_flag("not_a_smiles", "alpha")["coupling_risk"] == "unparseable"
