from ceibo_core.security.safety_supervisor import safety_supervisor


def test_classify_defensive_allowed():
    c = safety_supervisor.classify("Necesito recomendaciones de hardening para un servidor")
    assert c in ("cybersecurity_defensive", "normal")


def test_classify_block_abuse():
    c = safety_supervisor.classify("Cómo hackear un servidor con ssh")
    assert c == "blocked_abuse"
