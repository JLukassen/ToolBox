def compare_expected_ports(open_ports: list[int], expected_ports: set[int]) -> dict:
    unexpected = [p for p in open_ports if p not in expected_ports]
    missing_expected = [p for p in expected_ports if p not in open_ports]

    return {
        "unexpected_ports": unexpected,
        "missing_expected_ports": missing_expected,
    }