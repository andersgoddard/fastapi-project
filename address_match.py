import math
import re
from collections import Counter
from ukaddresskit.parser import tag

WORD = re.compile(r"\w+")

STREET_KEYWORDS = (
    "street", "road", "avenue", "lane", "drive",
    "close", "court", "place", "crescent", "grove",
    "terrace", "way", "row", "square", "gardens", "gate", "mews"
)

FLOOR_EXPANSIONS = {
    r"\bgff\b": "ground",
    r"\bgf\b": "ground",
    r"\blgf\b": "basement",
    r"\bbf\b": "basement",
    r"\btff\b": "first",
    r"\btf\b": "first",
    r"\b1ff\b": "first",
    r"\b2ff\b": "second",
    r"\b3ff\b": "third",
    r"\b4ff\b": "fourth",
    r"\buf\b": "upper",
    r"\bum\b": "upper",
}

REMOVE_UNIT_WORDS = {
    "floor",
    "flat",
    "maisonette",
    "apartment",
}

# --------------------------------------------------
# Component normalisation helpers
# --------------------------------------------------

def normalise_units(text: str) -> str:
    if not text:
        return text

    t = text.lower()

    for pattern, replacement in FLOOR_EXPANSIONS.items():
        t = re.sub(pattern, replacement, t)

    tokens = re.findall(r"[a-z0-9']+", t)
    tokens = [t for t in tokens if t not in REMOVE_UNIT_WORDS]

    return " ".join(tokens)


def normalise_split_numbers(components: dict) -> dict:
    """
    Fix cases like:
    BuildingNumber = '8 16A'
    → SubBuildingName='8', BuildingNumber='16A'
    """
    bn = components.get("BuildingNumber")
    sb = components.get("SubBuildingName")

    if bn and not sb:
        parts = bn.split()
        if len(parts) == 2:
            components["SubBuildingName"] = parts[0]
            components["BuildingNumber"] = parts[1]

    return components


def normalise_component_text(components: dict) -> dict:
    for key in ("SubBuildingName", "BuildingName"):
        if components.get(key):
            components[key] = normalise_units(components[key])
    return components


def get_effective_street(components: dict):
    street = components.get("StreetName")
    locality = components.get("Locality")

    if street:
        if locality and any(k in locality.lower() for k in STREET_KEYWORDS):
            return f"{street} {locality}"
        return street

    if locality and any(k in locality.lower() for k in STREET_KEYWORDS):
        return locality

    return None

# --------------------------------------------------
# Address normalisation (ONE parse only)
# --------------------------------------------------

def normalise_address(raw_address):
    if not raw_address or not isinstance(raw_address, str):
        return "", {}

    components = tag(raw_address) or {}
    components = normalise_split_numbers(components)
    components = normalise_component_text(components)
    effective_street = get_effective_street(components)

    normalised_parts = [
        components.get("SubBuildingName"),
        components.get("BuildingName"),
        components.get("BuildingNumber"),
        effective_street,
        components.get("Postcode"),
    ]

    cleaned = [
        p.lower().strip()
        for p in normalised_parts
        if p
    ]

    return " ".join(cleaned), components


# --------------------------------------------------
# Vectorisation & cosine similarity
# --------------------------------------------------

GARDEN_EQUIVALENCE = {
    "garden": {"ground", "basement"},
}

def reconcile_garden_units(vec1: Counter, vec2: Counter):
    for garden, equivalents in GARDEN_EQUIVALENCE.items():
        for equiv in equivalents:
            if (
                garden in vec1 and equiv in vec2
            ) or (
                garden in vec2 and equiv in vec1
            ):
                vec1.pop(garden, None)
                vec1.pop(equiv, None)
                vec2.pop(garden, None)
                vec2.pop(equiv, None)

    return vec1, vec2


def text_to_vector(text):
    return Counter(WORD.findall(text))


def get_cosine(vec1, vec2):
    intersection = set(vec1) & set(vec2)
    numerator = sum(vec1[x] * vec2[x] for x in intersection)

    sum1 = sum(v ** 2 for v in vec1.values())
    sum2 = sum(v ** 2 for v in vec2.values())

    if not sum1 or not sum2:
        return 0.0

    return numerator / (math.sqrt(sum1) * math.sqrt(sum2))

# --------------------------------------------------
# Numeric reconciliation helpers
# --------------------------------------------------

def extract_numeric_tokens(components: dict) -> set:
    nums = set()
    for key in ("BuildingNumber", "SubBuildingName"):
        val = components.get(key)
        if val:
            for match in re.findall(r"\d+[a-zA-Z]?", val):
                nums.add(match.lower())
    return nums


# --------------------------------------------------
# Penalisation logic
# --------------------------------------------------

def penalise_number_mismatch(cosine, internal, external):
    # High-confidence reconciliation
    if cosine >= 0.98:
        nums_i = extract_numeric_tokens(internal)
        nums_e = extract_numeric_tokens(external)

        if len(nums_i | nums_e) == 1:
            return cosine

    house_i = internal.get("BuildingNumber")
    house_e = external.get("BuildingNumber")
    flat_i = internal.get("SubBuildingName")
    flat_e = external.get("SubBuildingName")

    multiplier = 1.0

    if house_i and house_e and house_i != house_e:
        multiplier *= 0.70

    if flat_i and flat_e and flat_i != flat_e:
        multiplier *= 0.70

    if bool(flat_i) != bool(flat_e):
        multiplier *= 0.70

    if not flat_i and not flat_e and bool(house_i) != bool(house_e):
        multiplier *= 0.70

    return cosine * multiplier

# -------------------------
# Main similarity function
# -------------------------

def score_address_pairs(pairs):
    results = []

    for pair in pairs:
        address1 = pair["address1"]
        address2 = pair["address2"]

        reapit_norm, reapit_comp = normalise_address(address1)
        propalt_norm, propalt_comp = normalise_address(address2)

        v1 = text_to_vector(reapit_norm)
        v2 = text_to_vector(propalt_norm)

        v1, v2 = reconcile_garden_units(v1, v2)

        cosine = get_cosine(v1, v2)
        cosine = penalise_number_mismatch(
            cosine, reapit_comp, propalt_comp
        )

        results.append({
            "address1": address1,
            "address2": address2,
            "similarity": cosine
        })

    return results

# --------------------------------------------------
# Debug helper
# --------------------------------------------------

def get_cosine_similarity(a, b):
    a_norm, a_comp = normalise_address(a)
    b_norm, b_comp = normalise_address(b)

    print(a_norm)
    print(a_comp)
    print(b_norm)
    print(b_comp)

    v1 = text_to_vector(a_norm)
    v2 = text_to_vector(b_norm)

    v1, v2 = reconcile_garden_units(v1, v2)

    cosine = get_cosine(v1, v2)
    print("cosine:", cosine)

    cosine = penalise_number_mismatch(cosine, a_comp, b_comp)
    print("penalised:", cosine)


# --------------------------------------------------
# Test
# --------------------------------------------------

# get_cosine_similarity(
    # "137-139 Gloucester Terrace Bayswater London W2 6DX",	"FLAT 9 137-139 GLOUCESTER TERRACE LONDON W2 6DX"
# )
