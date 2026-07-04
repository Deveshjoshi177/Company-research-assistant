import os
import re
import json
import requests
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==========================================
# 1. CORE API INTEGRATIONS (SERPER & OPENROUTER)
# ==========================================

def get_official_website(company_name):
    """Uses Serper.dev to find the most likely official domain for a company name."""
    serper_api_key = os.environ.get('SERPER_API_KEY') or st.session_state.get('SERPER_API_KEY')
    if not serper_api_key:
        return None
    
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": f"{company_name} official website home page"})
    headers = {'X-API-KEY': serper_api_key, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            results = response.json()
            organic = results.get('organic', [])
            if organic:
                return organic[0].get('link')
    except Exception:
        pass
    return None

def search_public_intel(query):
    """Gathers auxiliary data and competitor hints from Serper.dev."""
    serper_api_key = os.environ.get('SERPER_API_KEY') or st.session_state.get('SERPER_API_KEY')
    if not serper_api_key:
        return ""
        
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

def ask_openrouter(model_id, prompt):
    """Communicates with chosen model via OpenRouter API."""
    api_key = os.environ.get('OPENROUTER_API_KEY') or st.session_state.get('OPENROUTER_API_KEY')
    if not api_key:
        return "Error: Missing OpenRouter API Key."

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Hackathon Research Bot"
    }
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"AI Generation Error ({response.status_code}): {response.text}"
    except Exception as e:
        return f"Exception occurred during AI generation: {e}"


# ==========================================
# 2. ADVANCED WEBSITE CRAWLER ENGINE
# ==========================================

def intelligent_crawl(base_url, max_pages=5):
    """Discovers internal pages, ignores auth/duplicates, and extracts meaningful body text."""
    crawled_content = []
    visited_urls = set()
    urls_to_visit = [base_url]
    
    keywords = ['about', 'product', 'service', 'solution', 'contact', 'pricing', 'overview']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Platforms'}
    
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    
    while urls_to_visit and len(visited_urls) < max_pages:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls:
            continue
            
        if any(x in current_url.lower() for x in ['login', 'signup', 'signin', 'cart', 'checkout', 'wp-admin']):
            continue
            
        try:
            visited_urls.add(current_url)
            res = requests.get(current_url, headers=headers, timeout=5)
            if res.status_code != 200 or 'text/html' not in res.headers.get('Content-Type', ''):
                continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for script in soup(["script", "style", "footer", "nav", "header"]):
                script.decompose()
            text = soup.get_text(separator=' ')
            clean_text = re.sub(r'\s+', ' ', text).strip()
            if len(clean_text) > 100:
                crawled_content.append(f"--- Page: {current_url} ---\n{clean_text[:2000]}")
                
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                parsed_full = urlparse(full_url)
                
                if parsed_full.netloc == base_domain and full_url not in visited_urls:
                    if any(kw in full_url.lower() for kw in keywords) or full_url == base_url:
                        if full_url not in urls_to_visit:
                            urls_to_visit.append(full_url)
                            
        except Exception:
            continue
            
    return "\n\n".join(crawled_content)


# ==========================================
# 3. PDF REPORT ENGINE (BLACK/GOLD LAYOUT)
# ==========================================

def create_pdf_report(filename, analysis_data, raw_metadata):
    """Generates a structured, professional corporate PDF document matching the custom branding."""
    doc = SimpleDocTemplate(
        filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=0, bottomMargin=40
    )
    elements = []
    styles = getSampleStyleSheet()
    
    brand_gold = colors.HexColor("#C89B3C")
    black = colors.black
    grey_line = colors.HexColor("#E0E0E0")
    
    style_normal = styles["Normal"]
    style_normal.leading = 14 
    
    # HEADER SECTION
    header_data = [
        [Paragraph("<font color='#C89B3C'><b>COMPANY RESEARCH REPORT</b></font>", style_normal)],
        [Paragraph(f"<font color='white' size=22><b>{raw_metadata['name']}</b></font>", style_normal)]
    ]
    header_table = Table(header_data, colWidths=[doc.width])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), black),
        ('PADDING', (0,0), (-1,-1), 20),
        ('BOTTOMPADDING', (0,1), (-1,1), 25),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20))

    def add_section_header(title):
        p = Paragraph(f"<font color='#C89B3C'><b>{title.upper()}</b></font>", style_normal)
        t = Table([[p]], colWidths=[doc.width])
        t.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 1, grey_line),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 15),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

    # COMPANY INFO
    add_section_header("COMPANY INFORMATION")
    info_table_data = [
        [Paragraph("Website", style_normal), Paragraph(raw_metadata['url'], style_normal)],
        [Paragraph("Contact Data", style_normal), Paragraph(raw_metadata['contact'], style_normal)]
    ]
    info_table = Table(info_table_data, colWidths=[1.5 * 72, doc.width - (1.5 * 72)])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # DYNAMIC CONTENT PARSING
    sections = analysis_data.split('\n\n')
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        if sec.startswith('###') or sec.startswith('##'):
            clean_header = sec.replace('#', '').strip()
            add_section_header(clean_header)
        else:
            clean_text = sec.replace('**', '').replace('*', '•').strip()
            elements.append(Paragraph(clean_text, style_normal))
            elements.append(Spacer(1, 6))
            
    doc.build(elements)


# ==========================================
# 4. DISCORD BOT WORKFLOW AUTOMATION
# ==========================================

def dispatch_to_discord(bot_token, channel_id, applicant_name, applicant_email, company_name, company_url, pdf_path):
    """Sends applicant information and attaches the generated PDF report to a Discord channel."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {bot_token}"}
    
    content_payload = (
        f"🚨 **New Research Report Generated** 🚨\n\n"
        f"**Applicant Name:** {applicant_name if applicant_name else 'N/A'}\n"
        f"**Applicant Email:** {applicant_email if applicant_email else 'N/A'}\n"
        f"**Company Researched:** {company_name}\n"
        f"**Company Website:** {company_url}\n"
    )
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (f"{company_name}_Report.pdf", f, 'application/pdf')}
            data = {'content': content_payload}
            res = requests.post(url, headers=headers, data=data, files=files, timeout=15)
            return res.status_code in [200, 201]
    except Exception as e:
        st.error(f"Discord Dispatch Error: {e}")
        return False


# ==========================================
# 5. STREAMLIT UI & DASHBOARD LOGIC
# ==========================================

st.set_page_config(page_title="AI Company Research Assistant", page_icon="🧠", layout="wide")

# CSS Highlights
st.markdown("""
    <style>
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        border: 2px solid #4F8BF9 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        padding: 5px;
        transition: all 0.3s ease;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        box-shadow: 0 4px 12px rgba(79, 139, 249, 0.4) !important;
        border-color: #2b6bec !important;
    }
    </style>
""", unsafe_allow_html=True)

# State Management
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "report_markdown" not in st.session_state:
    st.session_state.report_markdown = ""
if "meta" not in st.session_state:
    st.session_state.meta = {}

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.title("Settings & Config")
    model_choice = st.selectbox(
        "Select AI Processing Model", 
        ["openrouter/free", "google/gemma-2-9b-it:free", "meta-llama/llama-3-8b-instruct:free", "mistralai/mistral-7b-instruct:free"]
    )
    
    st.markdown("---")
    with st.expander("Discord Integration Setup", expanded=True):
        app_name = st.text_input("Applicant Name", placeholder="Enter your full name", value="")
        app_email = st.text_input("Applicant Email Address", placeholder="e.g., user@example.com", value="")
        bot_token = st.text_input("Discord Bot Token", type="password", placeholder="Paste Bot Token here...")
        chan_id = st.text_input("Discord Channel ID", placeholder="e.g., 123456789012345678")

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #888888; font-size: 0.85rem; padding-top: 10px;">
            🔒 <b>AI System Secured</b><br>
            Developed & Owned by <br>
            <span style="color: #ff4b4b; font-weight: bold;">Devesh Joshi</span>
        </div>
        """, 
        unsafe_allow_html=True
    )

# --- MAIN DASHBOARD INTERFACE ---
st.title("💭 Intelligent AI Research System")
st.write("Provide a target company name or explicit web URL to crawl pages, parse external public records, discover direct domain competitors, and generate professional intelligence summaries.")
st.markdown("<br>", unsafe_allow_html=True) 

input_query = st.text_input("Enter Company Name or Complete Website URL:", placeholder="e.g., 'Stripe' or 'https://tesla.com'")

if st.button("Generate Intelligence Report", type="primary"):
    if not input_query.strip():
        st.warning("⚠️ Please enter a company name or URL to begin the research.")
    else:
        target_name = ""
        target_url = ""
        
        with st.status("Initializing Intelligence Pipeline...", expanded=True) as status:
            if input_query.startswith("http://") or input_query.startswith("https://"):
                target_url = input_query
                parsed = urlparse(target_url)
                target_name = parsed.netloc.replace("www.", "").split('.')[0].capitalize()
            else:
                target_name = input_query
                status.update(label=f"Locating official digital domain for '{target_name}' via Serper.dev...")
                target_url = get_official_website(target_name)
                if not target_url:
                    target_url = f"https://www.google.com/search?q={target_name}"
            
            status.update(label=f"Crawling deep assets from {target_url}...")
            crawled_text = ""
            if target_url.startswith("http"):
                crawled_text = intelligent_crawl(target_url, max_pages=5)
            
            status.update(label="Scanning public records for metadata and address maps...")
            meta_intel = search_public_intel(f"{target_name} headquarters contact address phone number")
            comp_intel = search_public_intel(f"{target_name} core direct market competitors and alternative alternatives")
            
            status.update(label="Executing multi-layer AI synthesis analysis parsing...")
            prompt = f"""
            You are an expert financial analyst. Analyze this gathered intelligence to build a formal market research brief.
            Target Company: {target_name}
            Primary Website Reference: {target_url}
            
            Raw Crawled Context from Site Pages:
            {crawled_text[:6000]}
            
            Auxiliary Search Indicators:
            {meta_intel} {comp_intel}
            
            Generate your structural breakdown exactly with these sections markdown headers:
            ### Executive Summary
            (Provide a comprehensive overview of the company)
            
            ### Offerings & Product Ecosystem
            (Detail their core products/services)
            
            ### Core Pain Points Addressed
            (List AI-generated business pain points they solve for their clients)
            
            ### Direct Market Competitors
            (Explicitly identify and construct a list of top competitors along with their respective websites)
            """
            
            analysis_output = ask_openrouter(model_choice, prompt)
            
            contact_info = "Extracted from public records / Search context"
            phone_match = re.search(r'\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', meta_intel)
            if phone_match:
                contact_info = phone_match.group(0)
                
            st.session_state.meta = {
                "name": target_name,
                "url": target_url,
                "contact": contact_info
            }
            st.session_state.report_markdown = analysis_output
            st.session_state.analysis_complete = True
            status.update(label="Analysis Pipeline complete!", state="complete", expanded=False)
            
        st.balloons()


# ==========================================
# 6. PREMIUM DASHBOARD RESULTS OUTPUT
# ==========================================
if st.session_state.analysis_complete:
    st.markdown("---")
    
    # Custom CSS for Premium Dark Theme Layout
    st.markdown("""
        <style>
        .report-container {
            background-color: #0E1117;
            border: 1px solid #1E2329;
            border-radius: 12px;
            padding: 30px;
            color: #E2E8F0;
            font-family: 'Inter', sans-serif;
            margin-bottom: 20px;
        }
        .report-title {
            font-size: 32px;
            font-weight: 700;
            color: #FFFFFF;
            margin-bottom: 5px;
        }
        .report-url {
            color: #F6AD55;
            font-size: 14px;
            text-decoration: none;
            margin-bottom: 25px;
            display: block;
        }
        .metric-card {
            background-color: #151921;
            border: 1px solid #2D3748;
            border-radius: 8px;
            padding: 15px 20px;
            height: 100%;
        }
        .metric-label {
            font-size: 10px;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 14px;
            color: #E2E8F0;
        }
        .section-header {
            font-size: 12px;
            color: #7F9CF5;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 25px 0 15px 0;
            font-weight: 600;
        }
        .pain-points-header { color: #F6AD55; }
        .pill {
            background-color: #1A202C;
            border: 1px solid #2D3748;
            color: #A3BFFA;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            display: inline-block;
            margin: 0 8px 8px 0;
        }
        .pain-point-item {
            font-size: 14px;
            color: #CBD5E0;
            margin-bottom: 12px;
            line-height: 1.5;
            display: flex;
        }
        .pain-point-item::before {
            content: "•";
            color: #F6AD55;
            font-weight: bold;
            margin-right: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Extract dynamic content from AI markdown
    raw_md = st.session_state.report_markdown
    products = [p.replace('*', '').replace('-', '').strip() for p in raw_md.split('\n') if 'product' in p.lower() or 'service' in p.lower() or p.strip().startswith('-')][:5]
    if not products: products = ["Core Software Platform", "Enterprise Solutions", "Developer APIs"]

    # Render HTML Layout
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
        <div>
            {''.join([f'<div class="pill">{p}</div>' for p in products])}
        </div>

        <div class="section-header pain-points-header">AI-Generated Market Assessment</div>
        <div class="pain-point-item">Extensive market positioning breakdown and competitive landscape analysis.</div>
        <div class="pain-point-item">Identification of core operational friction points solved by ecosystem.</div>
        <div class="pain-point-item">Review full structural analysis in the generated corporate PDF below.</div>
    </div>
    """
    
    st.markdown(html_content, unsafe_allow_html=True)
    
    # Action Buttons Layer
    col1, col2, col3 = st.columns([1, 1, 3])
    
    pdf_filename = "Intelligence_Report.pdf"
    create_pdf_report(pdf_filename, st.session_state.report_markdown, st.session_state.meta)
    
    with col1:
        with open(pdf_filename, "rb") as pdf_file:
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_file,
                file_name=f"{st.session_state.meta['name']}_Intelligence_Report.pdf",
                mime="application/pdf",
                type="primary", 
                use_container_width=True
            )
            
    with col2:
        if bot_token and chan_id:
            success = dispatch_to_discord(
                bot_token, chan_id, app_name, app_email, 
                st.session_state.meta['name'], st.session_state.meta['url'], pdf_filename
            )
            if success:
                st.button("✔️ Sent to Discord", disabled=True, use_container_width=True)
            else:
                st.button("❌ Discord Error", disabled=True, use_container_width=True)
