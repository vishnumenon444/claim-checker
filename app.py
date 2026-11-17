import re
import json
import streamlit as st
from pypdf import PdfReader
from google import genai

st.set_page_config(page_title="ClaimCheck for Patent Attorneys", page_icon="⚖️", layout="wide")

MODEL = "gemini-3.8-flash"

# ---------- Look and feel: black and gold ----------
CSS = (
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=Poppins:wght@300;400;500;600&display=swap');"
    ".block-container{padding-top:1.5rem;max-width:1200px;}"
    ".hero{position:relative;overflow:hidden;background:radial-gradient(circle at 85% 20%,#3A2E0B 0%,#14110A 45%,#0A0A0A 100%);"
    "border:1px solid #C9A227;border-radius:18px;padding:34px 40px;display:flex;align-items:center;"
    "justify-content:space-between;gap:24px;margin-bottom:20px;"
    "box-shadow:0 8px 24px rgba(0,0,0,0.35);}"
    ".hero-text{max-width:700px;}"
    ".badge{display:inline-block;font-family:'Poppins',sans-serif;background:linear-gradient(90deg,#E6C34A,#B8901F);"
    "color:#111;font-weight:600;font-size:0.72rem;letter-spacing:2px;padding:5px 14px;border-radius:20px;margin-bottom:14px;}"
    ".title{font-family:'Playfair Display',Georgia,serif;font-weight:700;font-size:2.7rem;line-height:1.1;"
    "margin:0 0 10px 0;padding:0;color:#F5E6B3;}"
    ".title span{background:linear-gradient(90deg,#F7DC6F,#C9A227);-webkit-background-clip:text;"
    "-webkit-text-fill-color:transparent;}"
    ".rule{width:90px;height:3px;background:linear-gradient(90deg,#E6C34A,transparent);border-radius:3px;margin:0 0 14px 0;}"
    ".sub{font-family:'Poppins',sans-serif;font-weight:300;color:#D9D2BC;margin:0;padding:0;font-size:1.02rem;line-height:1.6;}"
    ".cards{display:flex;gap:14px;margin-bottom:20px;flex-wrap:wrap;}"
    ".card{flex:1;min-width:220px;border-radius:14px;padding:16px 18px;background:#FBF8EE;"
    "border:1px solid #E9DDB0;border-top:4px solid #C9A227;color:#1A1A1A;font-family:'Poppins',sans-serif;}"
    ".card h4{margin:0 0 6px 0;padding:0;font-size:1.02rem;font-weight:600;color:#14110A;}"
    ".card p{margin:0;font-size:0.88rem;color:#4A4636;}"
    "button[data-baseweb='tab']{font-size:1.02rem;font-weight:600;}"
    ".stButton>button{background:#111;color:#E6C34A;border:1px solid #C9A227;border-radius:10px;"
    "padding:0.55rem 1.4rem;font-weight:600;}"
    ".stButton>button:hover{background:#C9A227;color:#111;border:1px solid #C9A227;}"
    ".footer{text-align:center;color:#7A7260;font-size:0.82rem;margin-top:30px;}"
    "@media (max-width:700px){.hero{flex-direction:column;text-align:center;padding:26px 20px;}.title{font-size:2rem;}.rule{margin:0 auto 14px auto;}}"
    "</style>"
)

SVG = (
    "<svg width='190' height='140' viewBox='0 0 190 140' xmlns='http://www.w3.org/2000/svg'>"
    "<rect x='18' y='12' width='88' height='116' rx='8' fill='#FBF8EE' stroke='#C9A227' stroke-width='2'/>"
    "<rect x='18' y='12' width='88' height='22' rx='8' fill='#C9A227'/>"
    "<text x='62' y='28' font-size='11' font-weight='bold' fill='#111' text-anchor='middle' font-family='Georgia,serif' letter-spacing='2'>PATENT</text>"
    "<rect x='30' y='46' width='64' height='5' rx='2' fill='#2B2B2B'/>"
    "<rect x='30' y='58' width='50' height='5' rx='2' fill='#8A7A3A'/>"
    "<rect x='30' y='70' width='58' height='5' rx='2' fill='#8A7A3A'/>"
    "<rect x='30' y='82' width='42' height='5' rx='2' fill='#8A7A3A'/>"
    "<circle cx='80' cy='108' r='10' fill='#111'/>"
    "<path d='M75 108 l4 4 l7 -8' fill='none' stroke='#E6C34A' stroke-width='3' stroke-linecap='round'/>"
    "<circle cx='142' cy='46' r='22' fill='#E6C34A'/>"
    "<circle cx='142' cy='46' r='22' fill='none' stroke='#FFF3B0' stroke-width='2' opacity='0.7'/>"
    "<rect x='134' y='65' width='16' height='10' rx='3' fill='#8A7A3A'/>"
    "<path d='M142 31 v-9 M124 37 l-7 -5 M160 37 l7 -5' stroke='#E6C34A' stroke-width='3' stroke-linecap='round'/>"
    "<circle cx='148' cy='104' r='15' fill='none' stroke='#C9A227' stroke-width='8' stroke-dasharray='7 5'/>"
    "<circle cx='148' cy='104' r='5' fill='#C9A227'/>"
    "<circle cx='174' cy='88' r='9' fill='none' stroke='#F7DC6F' stroke-width='5' stroke-dasharray='5 4'/>"
    "</svg>"
)

HERO = (
    "<div class='hero'><div class='hero-text'>"
    "<span class='badge'>FREE BETA</span>"
    "<div class='title'>ClaimCheck <span>for Patent Attorneys</span></div>"
    "<div class='rule'></div>"
    "<p class='sub'>Catch claim errors early and understand office actions faster. "
    "Use public patent text only while testing.</p></div>" + SVG + "</div>"
)

CARDS = (
    "<div class='cards'>"
    "<div class='card'><h4>📝 Antecedent basis</h4><p>Finds \"the\" or \"said\" terms that were never introduced with \"a\" or \"an\".</p></div>"
    "<div class='card'><h4>🔢 Reference numerals</h4><p>Matches numerals in the claims with the description.</p></div>"
    "<div class='card'><h4>📄 Office action summary</h4><p>Turns an examiner's letter into a clear table of rejections.</p></div>"
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


tab1, tab2, tab3, tab4 = st.tabs(["📝 Antecedent basis", "🔢 Reference numerals", "📄 Office action summary", "🔒 Privacy"])

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
with tab4:
    st.subheader("Privacy and confidentiality")
    st.markdown("""
**This tool is in free beta. Please use public patent documents only.**

- **Antecedent basis and Reference numerals tabs:** your text is checked by rules inside this app. It is **not sent to any AI service** and this app does **not save it**.
- **Office action summary tab:** the text of the PDF you upload **is sent to Google's Gemini API** to produce the summary. During beta this uses a free tier, where the provider may use inputs to improve its models. **Do not upload confidential or unpublished client material.**
- This app does not store uploaded files or results, and has no user accounts.
- The app runs on Streamlit's hosting, which may keep standard technical logs.
- Before real client matters are supported, the AI step will move to a paid API whose terms say inputs are not used for training. This page will be updated when that happens.
- Results are a drafting aid, not legal advice. Always check them yourself.

Questions? Contact: your-email@example.com
""")
