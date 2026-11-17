import re
import json
import streamlit as st
from pypdf import PdfReader
from google import genai

st.set_page_config(page_title="ClaimCheck for Patent Attorneys", page_icon="⚖️", layout="wide")

MODEL = "gemini-3.8-flash"

# ---------- Look and feel (colors, banner, cards) ----------
CSS = (
    "<style>"
    ".block-container{padding-top:1.5rem;max-width:1200px;}"
    ".hero{background:linear-gradient(120deg,#0B2545 0%,#13498A 55%,#0B7285 100%);"
    "border-radius:18px;padding:28px 34px;display:flex;align-items:center;"
    "justify-content:space-between;gap:20px;color:white;margin-bottom:18px;"
    "box-shadow:0 6px 18px rgba(11,37,69,0.25);}"
    ".hero h1{color:white;margin:0 0 6px 0;font-size:2.1rem;line-height:1.15;}"
    ".hero p{color:#D6E8F5;margin:0;font-size:1.02rem;}"
    ".badge{display:inline-block;background:#F59F00;color:#2B1B00;font-weight:700;"
    "font-size:0.78rem;padding:3px 10px;border-radius:20px;margin-bottom:10px;}"
    ".cards{display:flex;gap:14px;margin-bottom:18px;flex-wrap:wrap;}"
    ".card{flex:1;min-width:220px;border-radius:14px;padding:16px 18px;color:#102A43;}"
    ".card h4{margin:0 0 6px 0;font-size:1.05rem;}"
    ".card p{margin:0;font-size:0.9rem;}"
    ".c1{background:#E3F2FD;border-left:6px solid #1C7ED6;}"
    ".c2{background:#E6FCF5;border-left:6px solid #0CA678;}"
    ".c3{background:#FFF4E6;border-left:6px solid #F76707;}"
    "button[data-baseweb='tab']{font-size:1.02rem;font-weight:600;}"
    ".stButton>button{background:linear-gradient(90deg,#13498A,#0B7285);color:white;"
    "border:0;border-radius:10px;padding:0.55rem 1.4rem;font-weight:600;}"
    ".stButton>button:hover{filter:brightness(1.12);color:white;}"
    ".footer{text-align:center;color:#6B7C8F;font-size:0.82rem;margin-top:30px;}"
    "@media (max-width:700px){.hero{flex-direction:column;text-align:center;}}"
    "</style>"
)

SVG = (
    "<svg width='190' height='130' viewBox='0 0 190 130' xmlns='http://www.w3.org/2000/svg'>"
    "<rect x='20' y='12' width='84' height='106' rx='8' fill='white'/>"
    "<rect x='20' y='12' width='84' height='20' rx='8' fill='#F59F00'/>"
    "<text x='62' y='27' font-size='11' font-weight='bold' fill='#2B1B00' text-anchor='middle'>PATENT</text>"
    "<rect x='32' y='44' width='60' height='5' rx='2' fill='#9FB7CC'/>"
    "<rect x='32' y='56' width='48' height='5' rx='2' fill='#9FB7CC'/>"
    "<rect x='32' y='68' width='56' height='5' rx='2' fill='#9FB7CC'/>"
    "<rect x='32' y='80' width='40' height='5' rx='2' fill='#9FB7CC'/>"
    "<circle cx='78' cy='101' r='9' fill='none' stroke='#0CA678' stroke-width='3'/>"
    "<path d='M73 101 l4 4 l7 -8' fill='none' stroke='#0CA678' stroke-width='3' stroke-linecap='round'/>"
    "<circle cx='140' cy='45' r='22' fill='#FFE066'/>"
    "<rect x='132' y='64' width='16' height='10' rx='3' fill='#CED4DA'/>"
    "<path d='M140 30 v-8 M123 36 l-6 -5 M157 36 l6 -5' stroke='#FFE066' stroke-width='3' stroke-linecap='round'/>"
    "<circle cx='146' cy='100' r='15' fill='none' stroke='#74C0FC' stroke-width='8' stroke-dasharray='7 5'/>"
    "<circle cx='146' cy='100' r='5' fill='#74C0FC'/>"
    "<circle cx='172' cy='84' r='9' fill='none' stroke='#63E6BE' stroke-width='5' stroke-dasharray='5 4'/>"
    "</svg>"
)

HERO = (
    "<div class='hero'><div>"
    "<span class='badge'>FREE BETA</span>"
    "<h1>ClaimCheck for Patent Attorneys</h1>"
    "<p>Catch claim errors early and understand office actions faster. "
    "Use public patent text only while testing.</p></div>" + SVG + "</div>"
)

CARDS = (
    "<div class='cards'>"
    "<div class='card c1'><h4>📝 Antecedent basis</h4><p>Finds \"the\" or \"said\" terms that were never introduced with \"a\" or \"an\".</p></div>"
    "<div class='card c2'><h4>🔢 Reference numerals</h4><p>Matches numerals in the claims with the description.</p></div>"
    "<div class='card c3'><h4>📄 Office action summary</h4><p>Turns an examiner's letter into a clear table of rejections.</p></div>"
    "</div>"
)

st.markdown(CSS, unsafe_allow_html=True)
st.markdown(HERO, unsafe_allow_html=True)
st.markdown(CARDS, unsafe_allow_html=True)

# ---------- Checking logic (unchanged) ----------
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


tab1, tab2, tab3 = st.tabs(["📝 Antecedent basis", "🔢 Reference numerals", "📄 Office action summary"])

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

st.markdown("<div class='footer'>ClaimCheck is a drafting aid, not legal advice. "
            "Always review results yourself.</div>", unsafe_allow_html=True)
