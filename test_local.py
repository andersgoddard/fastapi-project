from address_match import score_address_pairs

pairs = [
    {
        "address1": "137-139 Gloucester Terrace Bayswater London W2 6DX",
        "address2": "FLAT 9 137-139 GLOUCESTER TERRACE LONDON W2 6DX"
    },
    {
        "address1": "10 Downing Street London SW1A 2AA",
        "address2": "10 Downing St, Westminster, London SW1A 2AA"
    },
    {
        "address1": "12 Norcutt Road, Twickenham, TW2 6SR",
        "address2": "22 Norcutt Road, Twickenham, TW2 6SR"
    }
]

results = score_address_pairs(pairs)
print(results)
