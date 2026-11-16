import re
import streamlit as st

st.title("Patent Claim Checker")
st.write("Use public patent text only while testing.")

STOP = set("""of to for in on at by with from and or that which wherein comprising
comprises having has is are be being configured coupled connected adapted operable
arranged positioned disposed mounted attached when while whereby so as than into
onto the a an said""".split())
PUNCT = set(";:,.()")


def split_claims(text):
    parts = re.split(r"(?m)^\s*(\d+)\s*[\.\)]\s*", text)
    claims = {}
    for i in range(1, len(parts) - 1, 2):
        claims[int(parts[i])] = parts[i + 1].strip()
    return claims


def check_claim(text, introduced):
    words = re.findall(r"[a-z0-9\-]+|[;:,.()]", text.lower())
    problems = []
    i = 0
    while i < len(words):
        w = words[i]
        if w in ("a", "an", "the", "said"):
            j = i + 1
            phrase = []
            while (j < len(words) and words[j] not in STOP
                   and words[j] not in PUNCT and len(phrase) < 3):
                phrase.append(words[j])
                j += 1
            if phrase:
                term = " ".join(phrase)
                if w in ("a", "an"):
                    introduced.add(term)
                else:
                    heads = {t.split()[-1] for t in introduced}
                    if not any(p in heads for p in phrase):
                        problems.append(f'"{w} {term}"')
            i = j
        else:
            i += 1
    return list(dict.fromkeys(problems))


tab1, tab2 = st.tabs(["Antecedent basis", "Reference numerals"])

with tab1:
    claims_text = st.text_area("Claims (numbered 1., 2., 3. ...)", height=300, key="claims1")
    if st.button("Check claims"):
        claims = split_claims(claims_text)
        if not claims:
            st.error("I could not find numbered claims. Start each claim with 1. 2. 3.")
        all_terms = {}
        for n in sorted(claims):
            text = claims[n]
            m = re.search(r"claims?\s+(\d+)", text.lower())
            introduced = set(all_terms.get(int(m.group(1)), set())) if m else set()
            problems = check_claim(text, introduced)
            all_terms[n] = introduced
            if problems:
                st.warning(f"Claim {n}: possible antecedent basis problems: " + ", ".join(problems))
            else:
                st.success(f"Claim {n}: no problems found")

with tab2:
    st.write("Numerals in the claims must be in brackets, like: housing (10)")
    claims_text2 = st.text_area("Claims", height=200, key="claims2")
    desc_text = st.text_area("Description", height=200, key="desc2")
    if st.button("Check numerals"):
        claim_nums = {}
        for m in re.finditer(r"([a-z][a-z\-]*)\s*\((\d+[a-z]?)\)", claims_text2.lower()):
            claim_nums.setdefault(m.group(2), set()).add(m.group(1))
        desc_nums = set(re.findall(r"\b(\d+[a-z]?)\b", desc_text.lower()))
        if not claim_nums:
            st.error("No numerals found in the claims. Write them in brackets, like: housing (10)")
        else:
            for num in sorted(claim_nums):
                names = ", ".join(sorted(claim_nums[num]))
                if num not in desc_nums:
                    st.warning(f"Numeral {num} ({names}) is in the claims but not in the description")
                else:
                    st.success(f"Numeral {num} ({names}) found in the description")
                if len(claim_nums[num]) > 1:
                    st.warning(f"Numeral {num} is named differently in the claims: {names}")
