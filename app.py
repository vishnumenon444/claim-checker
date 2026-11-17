import re
import json
import streamlit as st
from pypdf import PdfReader
from google import genai
st.set_page_config(page_title="ClaimCheck for Patent Attorneys", page_icon="⚖️", layout="wide")
MODEL = "gemini-3.8-flash"

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


tab1, tab2, tab3 = st.tabs(["Antecedent basis", "Reference numerals", "Office action summary"])

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

with tab3:
    st.warning("Free AI tiers may use your inputs to improve their models. "
               "Upload PUBLIC office actions only.")
    pdf = st.file_uploader("Upload an office action (PDF)", type="pdf")
    if pdf and st.button("Summarize office action"):
        reader = PdfReader(pdf)
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        if len(text.strip()) < 200:
            st.error("I could not read text from this PDF. It may be a scanned image.")
        else:
            prompt = (
                "You are helping a patent attorney. Read this USPTO office action and "
                "return ONLY JSON with this shape: "
                '{"application_number": "", "summary": "", '
                '"rejections": [{"type": "", "claims": "", "references": "", "reasoning": ""}], '
                '"objections": ["..."]}. '
                "All values must be plain strings. Use only what the examiner wrote. "
                "Do not invent anything and do not write arguments. "
                "If something is missing, use an empty string.\n\n"
                "OFFICE ACTION TEXT:\n" + text[:60000]
            )
            try:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                resp = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                data = json.loads(resp.text)
                st.subheader("Summary")
                st.write(data.get("application_number", ""))
                st.write(data.get("summary", ""))
                st.subheader("Rejections")
                st.table(data.get("rejections", []))
                st.subheader("Objections")
                for o in data.get("objections", []):
                    st.write("- " + str(o))
                st.caption("AI-generated. Always check against the original office action.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")
