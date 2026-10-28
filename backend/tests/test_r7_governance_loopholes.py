# R7 governance — integrity loophole probes (expected to expose gaps; documents behaviour)
import secrets
from test_r7_governance_controls import GC, _login


def test_resolve_after_override_should_be_blocked():
    admin = _login("adminsupport@pmcmanagers.com", ["Admin@12345", "Admin@123"])
    com = _login("committee@pmcmanagers.com", ["Bid@1234"])
    ref = admin.post(f"{GC}/integrity-cases", json={"notice_ref": "TEST_R7_LH", "title": "TEST lh",
                                                    "reason": "probe loophole"}).json()["case_ref"]
    admin.post(f"{GC}/integrity-cases/senior-override", json={"case_ref": ref, "decision": "dismissed",
                                                              "reason": "Senior override for probe"})
    r = com.post(f"{GC}/integrity-cases/resolve", json={"case_ref": ref, "resolution": "upheld"})
    print("resolve-after-override:", r.status_code, r.text)
    assert r.status_code == 409


def test_reclassify_after_verify_by_other_user():
    admin = _login("adminsupport@pmcmanagers.com", ["Admin@12345", "Admin@123"])
    owner = _login("kannan@emeraldcorporates.com", ["Owner@123"])
    legal = _login("legal@pmcmanagers.com", ["Legal@123"])
    n = "TEST_R7_LH_" + secrets.token_hex(2)
    admin.post(f"{GC}/buyer-classifications", json={"notice_ref": n, "buyer_name": "TEST X",
                                                    "buyer_type": "public_sector", "basis": "probe"})
    legal.post(f"{GC}/buyer-classifications/verify", json={"notice_ref": n, "agree": True})
    # verified record silently overwritten back to pending by a reclassification
    r = owner.post(f"{GC}/buyer-classifications", json={"notice_ref": n, "buyer_name": "TEST X",
                                                        "buyer_type": "private_sector", "basis": "probe2"})
    print("reclassify-verified:", r.status_code, r.text)
    assert r.status_code in (409, 403)
