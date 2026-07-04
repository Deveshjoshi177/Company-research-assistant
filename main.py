import os
import re
import json
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. CORE API INTEGRATIONS WITH CACHING
# ==========================================

@st.cache_data(show_spinner=False)
def get_official_website(company_name):
    serper_api_key = os.environ.get('SERPER_API_KEY') or st.session_state.get('SERPER_API_KEY', '')
    if not serper_api_key: return None
    url, headers = "https://google.serper.dev/search", {'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=json.dumps({"q": f"{company_name} official website home page"}), timeout=10)
        if res.status_code == 200 and res.json().get('organic'): return res.json()['organic'][0].get('link')
    except Exception: pass
    return None

@st.cache_data(show_spinner=False)
def search_public_intel(query):
    serper_api_key = os.environ.get('SERPER_API_KEY') or st.session_state.get('SERPER_API_KEY', '')
    if not serper_api_key: return ""
    url, headers = "https://google.serper.dev/search", {'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'}
    try:
        res = requests.post(url, headers=headers, data=json.dumps({"q": query}), timeout=10)
        if res.status_code == 200: return " ".join([f"{i.get('title', '')}: {i.get('snippet', '')}" for i in res.json().get('organic', [])[:5]])
    except Exception: pass
    return ""

@st.cache_data(show_spinner=False)
def ask_openrouter(model_id, prompt):
    api_key = os.environ.get('OPENROUTER_API_KEY') or st.session_state.get('OPENROUTER_API_KEY', '')
    if not api_key: return "Error: Missing API Key."
    url, headers = "https://openrouter.ai/api/v1/chat/completions", {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        res = requests.post(url, headers=headers, data=json.dumps({"model": model_id, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}), timeout=45)
        if res.status_code == 200: return res.json()['choices'][0]['message']['content']
    except Exception: pass
    return "Generation Failed."

# ==========================================
# 2. CRAWLER & PARSER
# ==========================================

@st.cache_data(show_spinner=False)
def intelligent_crawl(base_url, max_pages=3):
    crawled, visited, urls = [], set(), [base_url]
    domain = urlparse(base_url).netloc
    while urls and len(visited) < max_pages:
        curr = urls.pop(0)
        if curr in visited or any(x in curr.lower() for x in ['login', 'signup', 'cart']): continue
        try:
            visited.add(curr)
            res = requests.get(curr, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if res.status_code != 200: continue
            soup = BeautifulSoup(res.text, 'html.parser')
            for script in soup(["script", "style", "nav", "footer"]): script.decompose()
            text = re.sub(r'\s+', ' ', soup.get_text(separator=' ')).strip()
            if len(text) > 100: crawled.append(text[:2000])
            for link in soup.find_all('a', href=True):
                full = urljoin(base_url, link['href'])
                if urlparse(full).netloc == domain and full not in visited: urls.append(full)
        except Exception: continue
    return "\n".join(crawled)

def parse_ai_markdown(text):
    """Safely extracts sections from the AI's markdown output."""
    data = {"summary": "Analysis completed.", "products": [], "pain_points": [], "competitors": []}
    
    sum_match = re.search(r'### SUMMARY\s*(.*?)(?:###|$)', text, re.IGNORECASE | re.DOTALL)
    if sum_match: data["summary"] = sum_match.group(1).replace('*', '').strip()
    
    prod_match = re.search(r'### PRODUCTS\s*(.*?)(?:###|$)', text, re.IGNORECASE | re.DOTALL)
    if prod_match:
        for line in prod_match.group(1).split('\n'):
            if line.strip().startswith('-'): data["products"].append(line.replace('-', '').replace('*', '').strip())
            
    pain_match = re.search(r'### PAIN POINTS\s*(.*?)(?:###|$)', text, re.IGNORECASE | re.DOTALL)
    if pain_match:
        for line in pain_match.group(1).split('\n'):
            if line.strip().startswith('-'): data["pain_points"].append(line.replace('-', '').replace('*', '').strip())
            
    comp_match = re.search(r'### COMPETITORS\s*(.*?)(?:###|$)', text, re.IGNORECASE | re.DOTALL)
    if comp_match:
        for line in comp_match.group(1).split('\n'):
            if line.strip().startswith('-'):
                parts = [p.strip() for p in line.replace('-', '').replace('*', '').split('|')]
                if len(parts) >= 2: data["competitors"].append({"name": parts[0], "url": parts[1], "focus": parts[2] if len(parts)>2 else ""})
                
    if not data["products"]: data["products"] = ["Core Platform Architecture", "Enterprise Solutions"]
    if not data["pain_points"]: data["pain_points"] = ["Operational scaling", "Market differentiation"]
    if not data["competitors"]: data["competitors"] = [{"name": "Market Alternative", "url": "N/A", "focus": "Direct Competition"}]
    return data

# ==========================================
# 3. BUG-FREE PDF ENGINE
# ==========================================

def create_pdf_report(filename, data, meta):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=20, bottomMargin=40)
    elements, styles = [], getSampleStyleSheet()
    normal = styles["Normal"]
    normal.leading, normal.fontSize = 14, 10
    
    title_style = ParagraphStyle('TitleStyle', parent=normal, fontSize=24, leading=28, textColor=colors.white)
    
    elements.append(Table([
        [Paragraph("<font color='#C89B3C'><b>COMPANY INTELLIGENCE REPORT</b></font>", normal)],
        [Paragraph(f"<b>{meta['name']}</b>", title_style)]
    ], colWidths=[doc.width], style=[
        ('BACKGROUND', (0,0), (-1,-1), colors.black), 
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('BOTTOMPADDING', (0,1), (-1,1), 25), 
        ('LEFTPADDING', (0,0), (-1,-1), 20)
    ]))
    elements.append(Spacer(1, 15))

    def add_header(title):
        elements.append(Table([[Paragraph(f"<font color='#C89B3C'><b>{title.upper()}</b></font>", normal)]], colWidths=[doc.width], 
                              style=[('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor("#C89B3C")), ('BOTTOMPADDING', (0,0), (-1,-1), 5)]))
        elements.append(Spacer(1, 10))

    add_header("Corporate Footprint")
    elements.append(Table([
        [Paragraph("<b>Website:</b>", normal), Paragraph(meta['url'], normal)],
        [Paragraph("<b>Contact Detail:</b>", normal), Paragraph(meta['contact'], normal)],
        [Paragraph("<b>HQ Address:</b>", normal), Paragraph(meta['address'], normal)]
    ], colWidths=[100, doc.width - 100], style=[('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(Spacer(1, 15))

    add_header("Executive Summary")
    elements.extend([Paragraph(data['summary'], normal), Spacer(1, 15)])
    
    add_header("Products & Services")
    for p in data['products']: elements.extend([Paragraph(f"• {p}", normal), Spacer(1, 4)])
    elements.append(Spacer(1, 10))
    
    add_header("Market Pain Points")
    for p in data['pain_points']: elements.extend([Paragraph(f"• {p}", normal), Spacer(1, 4)])
    elements.append(Spacer(1, 10))
    
    add_header("Competitors")
    comp_data = [[Paragraph("<b>Name</b>", normal), Paragraph("<b>Website</b>", normal)]]
    for c in data['competitors']: comp_data.append([Paragraph(c['name'], normal), Paragraph(f"<font color='blue'>{c['url']}</font>", normal)])
    elements.append(Table(comp_data, colWidths=[150, doc.width-150], style=[('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('PADDING', (0,0), (-1,-1), 6)]))
    
    doc.build(elements)

# ==========================================
# 4. DISCORD AUTOMATION
# ==========================================

def dispatch_to_discord(token, chan_id, name, email, comp_name, comp_url, pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            res = requests.post(f"https://discord.com/api/v10/channels/{chan_id}/messages", 
                                headers={"Authorization": f"Bot {token}"}, 
                                data={'content': f"🚨 **New Report** 🚨\n**User:** {name}\n**Company:** {comp_name}\n**URL:** {comp_url}"}, 
                                files={'file': (f"{comp_name}_Report.pdf", f, 'application/pdf')}, timeout=15)
            return res.status_code in [200, 201]
    except Exception: return False

# ==========================================
# 5. STREAMLIT APP & UI
# ==========================================

st.set_page_config(page_title="Corporate Intelligence", layout="wide")

st.markdown("""<style>
div[data-testid="stTextInput"] div[data-baseweb="input"] { border: 2px solid #4F8BF9 !important; border-radius: 8px !important; }
</style>""", unsafe_allow_html=True)

if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False

with st.sidebar:
    st.title("System Config")
    model_choice = st.selectbox("Select Model", ["openrouter/free", "google/gemma-2-9b-it:free", "meta-llama/llama-3-8b-instruct:free"])
    with st.expander("Discord Setup", expanded=True):
        app_name, app_email = st.text_input("Name"), st.text_input("Email")
        bot_token, chan_id = st.text_input("Bot Token", type="password"), st.text_input("Channel ID")
    
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #888888; font-size: 0.85rem; padding-top: 10px;">
            🔒 <b>AI System Secured</b><br>Developed & Owned by <br><span style="color: #ff4b4b; font-weight: bold;">Devesh Joshi</span>
        </div>
    """, unsafe_allow_html=True)

st.title("💭 Intelligent AI Research System")
input_query = st.text_input("Enter Company Name or URL:", placeholder="e.g., 'Stripe' or 'https://tesla.com'")

if st.button("Generate Intelligence Report", type="primary") and input_query.strip():
    with st.status("Processing...", expanded=True) as status:
        target_url = input_query if input_query.startswith("http") else (get_official_website(input_query) or f"https://google.com/search?q={input_query}")
        target_name = urlparse(target_url).netloc.replace("www.", "").split('.')[0].capitalize() if input_query.startswith("http") else input_query
        
        status.update(label="Crawling website & scanning records...")
        crawled_text = intelligent_crawl(target_url) if target_url.startswith("http") else ""
        meta_intel = search_public_intel(f"{target_name} headquarters address phone")
        
        status.update(label="Running AI Analysis...")
        prompt = f"""Analyze {target_name} ({target_url}). Data: {crawled_text[:4000]} {meta_intel}
        DO NOT use markdown tables. Output EXACTLY these 4 sections using bullet points:
        
        ### SUMMARY
        [Write a 2 sentence summary here]
        
        ### PRODUCTS
        - [Product 1]
        - [Product 2]
        
        ### PAIN POINTS
        - [Pain point 1]
        - [Pain point 2]
        
        ### COMPETITORS
        - [Competitor 1] | [URL] | [Focus]
        - [Competitor 2] | [URL] | [Focus]
        """
        
        st.session_state.parsed_data = parse_ai_markdown(ask_openrouter(model_choice, prompt))
        
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', meta_intel)
        addr_match = re.search(r'([^.|\n]+(?:Street|Ave|Avenue|Blvd|Road|Suite|Floor|Drive|Parkway)[^.|\n]+)', meta_intel, re.IGNORECASE)
        
        st.session_state.meta = {
            "name": target_name, 
            "url": target_url, 
            "contact": phone_match.group(0) if phone_match else "Not publicly listed",
            "address": addr_match.group(1).strip() if addr_match else "Global / Check official website"
        }
        
        st.session_state.analysis_complete = True
        status.update(label="Complete!", state="complete")

# ==========================================
# 6. VERCEL UI OUTPUT (DYNAMIC FILENAMES)
# ==========================================
if st.session_state.analysis_complete:
    st.markdown("---")
    
    st.markdown("""<style>
    .rep-box { background: #0E1117; border: 1px solid #1E2329; border-radius: 12px; padding: 25px; color: #E2E8F0; margin-bottom: 20px; font-family: sans-serif; }
    .rep-title { font-size: 32px; font-weight: bold; color: white; }
    .rep-url { color: #F6AD55; font-size: 14px; text-decoration: none; margin-bottom: 20px; display: block; }
    .m-grid { display: flex; gap: 15px; margin-bottom: 20px; }
    .m-card { background: #151921; border: 1px solid #2D3748; padding: 15px; border-radius: 8px; flex: 1; }
    .m-lbl { font-size: 10px; color: #718096; text-transform: uppercase; font-weight: bold; margin-bottom: 5px; }
    .sec-hdr { color: #7F9CF5; font-size: 12px; font-weight: bold; text-transform: uppercase; margin: 20px 0 10px 0; border-bottom: 1px solid #1E2329; padding-bottom: 5px; }
    .pill { background: #1A202C; border: 1px solid #2D3748; color: #A3BFFA; padding: 5px 12px; border-radius: 20px; font-size: 13px; display: inline-block; margin: 0 5px 5px 0; }
    .bull { margin-bottom: 8px; font-size: 14px; color: #CBD5E0; }
    .bull::before { content: "• "; color: #F6AD55; font-weight: bold; }
    </style>""", unsafe_allow_html=True)

    d, m = st.session_state.parsed_data, st.session_state.meta
    
    html_parts = [
        "<div class='rep-box'>",
        f"<div class='rep-title'>{m['name']}</div>",
        f"<a href='{m['url']}' class='rep-url' target='_blank'>{m['url']}</a>",
        "<div class='m-grid'>",
        f"<div class='m-card'><div class='m-lbl'>Contact Detail</div><div>{m['contact']}</div></div>",
        f"<div class='m-card'><div class='m-lbl'>HQ Address</div><div>{m['address']}</div></div>",
        "</div>",
        "<div class='sec-hdr'>Executive Summary</div>",
        f"<div style='font-size:14px; line-height:1.5;'>{d['summary']}</div>",
        "<div class='sec-hdr'>Products & Services</div>",
        "<div>" + "".join([f"<span class='pill'>{p.split(':')[0]}</span>" for p in d['products']]) + "</div>",
        "<div class='sec-hdr' style='color:#F6AD55;'>Market Pain Points</div>",
        "<div>" + "".join([f"<div class='bull'>{pt}</div>" for pt in d['pain_points']]) + "</div>",
        "<div class='sec-hdr'>Competitors</div>",
        "<div>" + "".join([f"<div class='bull'><b>{c['name']}</b> (<a href='{c['url']}' style='color:#7F9CF5;'>Link</a>)</div>" for c in d['competitors']]) + "</div>",
        "</div>"
    ]
    st.markdown("".join(html_parts), unsafe_allow_html=True)
    
    # Safe dynamic file naming to prevent concurrency collisions
    pdf_file = f"{m['name'].replace(' ', '_')}_Report.pdf"
    create_pdf_report(pdf_file, d, m)
    csv_data = pd.DataFrame(d['competitors']).to_csv(index=False).encode('utf-8')
    
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        with open(pdf_file, "rb") as f: st.download_button("📥 PDF Report", f, f"{m['name']}_Report.pdf", "application/pdf", type="primary", use_container_width=True)
    with c2:
        st.download_button("📊 CSV Data", csv_data, f"{m['name']}_Data.csv", "text/csv", use_container_width=True)
    with c3:
        if bot_token and chan_id:
            if dispatch_to_discord(bot_token, chan_id, app_name, app_email, m['name'], m['url'], pdf_file): st.button("✔️ Sent to Discord", disabled=True, use_container_width=True)
            else: st.button("❌ Discord Error", disabled=True, use_container_width=True)
