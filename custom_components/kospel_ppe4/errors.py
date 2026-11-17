"""Error and warning bit maps from the KOSPEL PPE4 manual EN-116B_f.1535."""
from __future__ import annotations

ERROR_BITS: dict[int, tuple[str, str]] = {
    0: ("E02", "Inlet temperature sensor failure (TIN)"),
    1: ("E03", "Outlet temperature sensor failure (TOUT)"),
    2: ("E04", "Temperature sensors reversed (OUT/IN)"),
    3: ("E05", "Air clog / flow meter failure (AIR2)"),
    4: ("E06", "Air clog / pressure switch / phase lost (AIR)"),
    5: ("E07", "Overtemperature (T MAX)"),
    6: ("E08", "Air clog / water pressure too high (FLOW)"),
    7: ("E09", "No mains grid sync / phase lost (3F)"),
    8: ("E10", "Illegal hardware configuration (CONFIG)"),
    9: ("E01", "Triac failure, isolate power"),
    10: ("E11", "Control system failure, isolate power"),
}

WARNING_BITS: dict[int, tuple[str, str]] = {
    0: ("W01", "AIR error while heating"),
    1: ("W02", "AIR2 error while heating"),
    2: ("W03", "FLOW error while heating"),
    3: ("W04", "T MAX error while heating"),
    4: ("W05", "Pressure switch / heater / triac failure"),
    5: ("W06", "Low battery"),
    6: ("W07", "Battery drained"),
    7: ("W08", "Temperature sensor response altered"),
    8: ("W09", "Control PCB failure"),
    9: ("W10", "Control PCB failure"),
    10: ("W11", "WiFi module failure"),
    11: ("W12", "Control PCB failure"),
    12: ("W13", "Environment out of limits / inlet sensor"),
    13: ("W14", "Outlet temperature sensor failed"),
    14: ("W15", "Environment out of limits / control PCB"),
    15: ("W16", "Environment out of limits / inlet sensor"),
    16: ("W17", "Environment out of limits / control PCB"),
}


def decode(word: int, bits: dict[int, tuple[str, str]]) -> list[str]:
    """Return the codes active in a 32-bit error word."""
    return [f"{code}: {description}" for bit, (code, description) in bits.items()
            if word & (1 << bit)]
