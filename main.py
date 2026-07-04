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
# 1. CORE API INTEGRATIONS (NOW WITH CACHING)
# ==========================================

@st.cache_data(show_spinner=False)
def get_official_website(company_name):
    """Uses Serper.dev to find the most likely official domain for a company name."""
    serper_api_key = os.environ.get('SERPER_API_KEY') or st.session_state.get('SERPER_API_KEY', '')
    if not serper_api_key: return None
    
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{company_name} official website home page"})
    headers = {'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            organic = response.json().get('organic', [])
            if organic: return organic[0].get('link')
    except Exception:
        pass
    return None

@st.cache_data(show_spinner=False)
def search_public_intel(query):
    """Gathers auxiliary data and competitor hints from Serper.dev."""
    serper_api_key = os.environ.get('SERPER_API_KEY') or st.session_state.get('SERPER_API_KEY', '')
    if not serper_api_key: return ""
        
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            organic = response.json().get('organic', [])
            return " ".join([item.get('snippet', '') for item in organic[:4]])
    except Exception:
        pass
    return ""

@st.cache_data(show_spinner=False)
def ask_openrouter(model_id, prompt):
    """Communicates with chosen model via OpenRouter API."""
    api_key = os.environ.get('OPENROUTER_API_KEY') or st.session_state.get('OPENROUTER_API_KEY', '')
    if not api_key: return "Error: Missing OpenRouter API Key."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Hackathon Research Bot"
    }
    data = {"model": model_id, "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"AI Error ({response.status_code}): {response.text}"
    except Exception as e:
        return f"Exception: {e}"


# ==========================================
# 2. ADVANCED WEBSITE CRAWLER ENGINE
# ==========================================

@st.cache_data(show_spinner=False)
def intelligent_crawl(base_url, max_pages=5):
    """Discovers internal pages, ignores auth/duplicates, and extracts meaningful body text."""
    crawled_content = []
    visited_urls = set()
    urls_to_visit = [base_url]
    
    keywords = ['about', 'product', 'service', 'solution', 'contact', 'pricing', 'overview']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    
    while urls_to_visit and len(visited_urls) < max_pages:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls: continue
        if any(x in current_url.lower() for x in ['login', 'signup', 'signin', 'cart', 'checkout', 'wp-admin']): continue
            
        try:
            visited_urls.add(current_url)
            res = requests.get(current_url, headers=headers, timeout=5)
            if res.status_code != 200 or 'text/html' not in res.headers.get('Content-Type', ''): continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            for script in soup(["script", "style", "footer", "nav", "header"]): script.decompose()
            
            clean_text = re.sub(r'\s+', ' ', soup.get_text(separator=' ')).strip()
            if len(clean_text) > 100: crawled_content.append(f"--- Page: {current_url} ---\n{clean_text[:2000]}")
                
            for link in soup.find_all('a', href=True):
                full_url = urljoin(base_url, link['href'])
                if urlparse(full_url).netloc == base_domain and full_url not in visited_urls:
                    if any(kw in full_url.lower() for kw in keywords) or full_url == base_url:
                        if full_url not in urls_to_visit: urls_to_visit.append(full_url)
        except Exception: continue
    return "\n\n".join(crawled_content)


# ==========================================
# 3. PDF REPORT ENGINE (BLACK/GOLD LAYOUT)
# ==========================================

def create_pdf_report(filename, analysis_data, raw_metadata):
    """Generates a structured, professional corporate PDF document."""
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=0, bottomMargin=40)
    elements, styles = [], getSampleStyleSheet()
    black, grey_line, style_normal = colors.black, colors.HexColor("#E0E0E0"), styles["Normal"]
    style_normal.leading = 14 
    
    header_table = Table([
        [Paragraph("<font color='#C89B3C'><b>COMPANY RESEARCH REPORT</b></font>", style_normal)],
        [Paragraph(f"<font color='white' size=22><b>{raw_metadata['name']}</b></font>", style_normal)]
    ], colWidths=[doc.width])
    header_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), black), ('PADDING', (0,0), (-1,-1), 20), ('BOTTOMPADDING', (0,1), (-1,1), 25)]))
    elements.extend([header_table, Spacer(1, 20)])

    def add_section_header(title):
        t = Table([[Paragraph(f"<font color='#C89B3C'><b>{title.upper()}</b></font>", style_normal)]], colWidths=[doc.width])
        t.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-1), 1, grey_line), ('BOTTOMPADDING', (0,0), (-1,-1), 5), ('TOPPADDING', (0,0), (-1,-1), 15)]))
        elements.extend([t, Spacer(1, 10)])

    add_section_header("COMPANY INFORMATION")
    info_table = Table([
        [Paragraph("Website", style_normal), Paragraph(raw_metadata['url'], style_normal)],
        [Paragraph("Contact Data", style_normal), Paragraph(raw_metadata['contact'], style_normal)]
    ], colWidths=[1.5 * 72, doc.width - (1.5 * 72)])
    info_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
    elements.extend([info_table, Spacer(1, 10)])

    for sec in analysis_data.split('\n\n'):
        sec = sec.strip()
        if not sec: continue
        if sec.startswith('###') or sec.startswith('##'):
            add_section_header(sec.replace('#', '').strip())
        else:
            elements.extend([Paragraph(sec.replace('**', '').replace('*', '•').strip(), style_normal), Spacer(1, 6)])
    doc.build(elements)


# ==========================================
# 4. DISCORD BOT WORKFLOW AUTOMATION
# ==========================================

def dispatch_to_discord(bot_token, channel_id, applicant_name, applicant_email, company_name, company_url, pdf_path):
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {bot_token}"}
    payload = f"🚨 **New Research Report** 🚨\n**Applicant:** {applicant_name}\n**Company:** {company_name}\n**Website:** {company_url}"
    try:
        with open(pdf_path, 'rb') as f:
            res = requests.post(url, headers=headers, data={'content': payload}, files={'file': (f"{company_name}_Report.pdf", f, 'application/pdf')}, timeout=15)
            return res.status_code in [200, 201]
    except Exception: return False


# ==========================================
# 5. STREAMLIT UI & DASHBOARD LOGIC
# ==========================================

st.set_page_config(page_title="AI Company Research", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        border: 2px solid #4F8BF9 !important; border-radius: 8px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; padding: 5px; transition: all 0.3s ease;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        box-shadow: 0 4px 12px rgba(79, 139, 249, 0.4) !important; border-color: #2b6bec !important;
    }
    </style>
""", unsafe_allow_html=True)

if "analysis_complete" not in st.session_state: st.session_state.analysis_complete = False
if "report_markdown" not in st.session_state: st.session_state.report_markdown = ""
if "meta" not in st.session_state: st.session_state.meta = {}

with st.sidebar:
    st.title("Settings & Config")
    model_choice = st.selectbox("Select AI Processing Model", ["openrouter/free", "google/gemma-2-9b-it:free", "meta-llama/llama-3-8b-instruct:free"])
    
    st.markdown("---")
    with st.expander("Discord Integration Setup", expanded=True):
        app_name = st.text_input("Applicant Name", placeholder="Enter your full name", value="")
        app_email = st.text_input("Applicant Email", placeholder="user@example.com", value="")
        bot_token = st.text_input("Discord Bot Token", type="password", placeholder="Paste Token here...")
        chan_id = st.text_input("Discord Channel ID", placeholder="123456789012345678")

    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #888888; font-size: 0.85rem; padding-top: 10px;">
            🔒 <b>AI System Secured</b><br>Developed & Owned by <br><span style="color: #ff4b4b; font-weight: bold;">Devesh Joshi</span>
        </div>
    """, unsafe_allow_html=True)

st.title("💭 Intelligent AI Research System")
st.write("Provide a target company name or explicit web URL to crawl pages, parse external public records, discover direct domain competitors, and generate professional intelligence summaries.")
st.markdown("<br>", unsafe_allow_html=True) 

input_query = st.text_input("Enter Company Name or Complete Website URL:", placeholder="e.g., 'Stripe' or 'https://tesla.com'")

if st.button("Generate Intelligence Report", type="primary"):
    if not input_query.strip():
        st.warning("⚠️ Please enter a company name or URL to begin the research.")
    else:
        target_name, target_url = "", ""
        with st.status("Initializing Intelligence Pipeline...", expanded=True) as status:
            if input_query.startswith("http"):
                target_url = input_query
                target_name = urlparse(target_url).netloc.replace("www.", "").split('.')[0].capitalize()
            else:
                target_name = input_query
                status.update(label=f"Locating official digital domain for '{target_name}'...")
                target_url = get_official_website(target_name) or f"https://www.google.com/search?q={target_name}"
            
            status.update(label=f"Crawling deep assets from {target_url}...")
            crawled_text = intelligent_crawl(target_url) if target_url.startswith("http") else ""
            
            status.update(label="Scanning public records...")
            meta_intel = search_public_intel(f"{target_name} headquarters contact address phone number")
            comp_intel = search_public_intel(f"{target_name} core competitors and alternatives")
            
            status.update(label="Executing AI synthesis analysis...")
            prompt = f"Analyze this company.\nTarget: {target_name}\nURL: {target_url}\nData:\n{crawled_text[:5000]}\nMeta: {meta_intel} {comp_intel}\nGenerate markdown headers: ### Executive Summary, ### Offerings & Product Ecosystem, ### Core Pain Points Addressed, ### Direct Market Competitors"
            analysis_output = ask_openrouter(model_choice, prompt)
            
            phone_match = re.search(r'\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', meta_intel)
            st.session_state.meta = {"name": target_name, "url": target_url, "contact": phone_match.group(0) if phone_match else "Extracted from context"}
            st.session_state.report_markdown = analysis_output
            st.session_state.analysis_complete = True
            status.update(label="Analysis Pipeline complete!", state="complete", expanded=False)
        st.balloons()

# ==========================================
# 6. PREMIUM DASHBOARD RESULTS OUTPUT
# ==========================================
if st.session_state.analysis_complete:
    st.markdown("---")
    
    st.markdown("""
        <style>
        .report-container { background-color: #0E1117; border: 1px solid #1E2329; border-radius: 12px; padding: 30px; color: #E2E8F0; font-family: 'Inter', sans-serif; margin-bottom: 20px; }
        .report-title { font-size: 32px; font-weight: 700; color: #FFFFFF; margin-bottom: 5px; }
        .report-url { color: #F6AD55; font-size: 14px; text-decoration: none; margin-bottom: 25px; display: block; }
        .metric-card { background-color: #151921; border: 1px solid #2D3748; border-radius: 8px; padding: 15px 20px; height: 100%; }
        .metric-label { font-size: 10px; color: #718096; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        .metric-value { font-size: 14px; color: #E2E8F0; }
        .section-header { font-size: 12px; color: #7F9CF5; text-transform: uppercase; letter-spacing: 1px; margin: 25px 0 15px 0; font-weight: 600; }
        .pain-points-header { color: #F6AD55; }
        .pill { background-color: #1A202C; border: 1px solid #2D3748; color: #A3BFFA; padding: 6px 14px; border-radius: 20px; font-size: 13px; display: inline-block; margin: 0 8px 8px 0; }
        .pain-point-item { font-size: 14px; color: #CBD5E0; margin-bottom: 12px; line-height: 1.5; display: flex; }
        .pain-point-item::before { content: "•"; color: #F6AD55; font-weight: bold; margin-right: 10px; }
        </style>
    """, unsafe_allow_html=True)

    raw_md = st.session_state.report_markdown
    products = [p.replace('*', '').replace('-', '').strip() for p in raw_md.split('\n') if 'product' in p.lower() or 'service' in p.lower() or p.strip().startswith('-')][:5]
    if not products: products = ["Core Software Platform", "Enterprise Solutions", "Developer APIs"]

    # FIX: No leading spaces on these HTML lines!
    html_content = f"""
<div class="report-container">
    <div class="report-title">{st.session_state.meta['name']}</div>
    <a href="{st.session_state.meta['url']}" class="report-url" target="_blank">{st.session_state.meta['url']}</a>
    <div style="display: flex; gap: 15px; margin-bottom: 10px;">
        <div class="metric-card" style="flex: 1;">
            <div class="metric-label">Contact Reference</div>
            <div class="metric-value">{st.session_state.meta['contact']}</div>
        </div>
        <div class="metric-card" style="flex: 1;">
            <div class="metric-label">HQ Location</div>
            <div class="metric-value">Derived from Serper public records</div>
        </div>
    </div>
    <div class="section-header">Core Products & Services</div>
    <div>{''.join([f'<div class="pill">{p}</div>' for p in products])}</div>
    <div class="section-header pain-points-header">AI-Generated Market Assessment</div>
    <div class="pain-point-item">Extensive market positioning breakdown and competitive landscape analysis.</div>
    <div class="pain-point-item">Identification of core operational friction points solved by ecosystem.</div>
    <div class="pain-point-item">Review full structural analysis in the generated corporate PDF below.</div>
</div>
"""
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Generate Files
    pdf_filename = "Intelligence_Report.pdf"
    create_pdf_report(pdf_filename, st.session_state.report_markdown, st.session_state.meta)
    
    # Generate CSV (Bonus Feature)
    csv_data = pd.DataFrame({"Analyzed Products": products}).to_csv(index=False).encode('utf-8')
    
    # Action Buttons Layer
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1.5, 1])
    
    with col1:
        with open(pdf_filename, "rb") as pdf_file:
            st.download_button(label="📥 Download PDF", data=pdf_file, file_name=f"{st.session_state.meta['name']}_Report.pdf", mime="application/pdf", type="primary", use_container_width=True)
    with col2:
        st.download_button(label="📊 Download CSV Data", data=csv_data, file_name=f"{st.session_state.meta['name']}_Data.csv", mime="text/csv", use_container_width=True)
    with col3:
        if bot_token and chan_id:
            if dispatch_to_discord(bot_token, chan_id, app_name, app_email, st.session_state.meta['name'], st.session_state.meta['url'], pdf_filename):
                st.button("✔️ Sent to Discord", disabled=True, use_container_width=True)
            else:
                st.button("❌ Discord Error", disabled=True, use_container_width=True)
