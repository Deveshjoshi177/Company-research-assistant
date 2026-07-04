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
    except Exception as e:
        st.error(f"Error fetching website lookup: {e}")
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
    
    # Target keywords that match meaningful pages
    keywords = ['about', 'product', 'service', 'solution', 'contact', 'pricing', 'overview']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Platforms'}
    
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    
    while urls_to_visit and len(visited_urls) < max_pages:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls:
            continue
            
        # Avoid login walls or duplicate structures
        if any(x in current_url.lower() for x in ['login', 'signup', 'signin', 'cart', 'checkout', 'wp-admin']):
            continue
            
        try:
            visited_urls.add(current_url)
            res = requests.get(current_url, headers=headers, timeout=5)
            if res.status_code != 200 or 'text/html' not in res.headers.get('Content-Type', ''):
                continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Text extraction
            for script in soup(["script", "style", "footer", "nav", "header"]):
                script.decompose()
            text = soup.get_text(separator=' ')
            clean_text = re.sub(r'\s+', ' ', text).strip()
            if len(clean_text) > 100:
                crawled_content.append(f"--- Page: {current_url} ---\n{clean_text[:2000]}")
                
            # Discover linked sub-pages dynamically
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                parsed_full = urlparse(full_url)
                
                # Verify domain constraints and target keyword structures
                if parsed_full.netloc == base_domain and full_url not in visited_urls:
                    if any(kw in full_url.lower() for kw in keywords) or full_url == base_url:
                        if full_url not in urls_to_visit:
                            urls_to_visit.append(full_url)
                            
        except Exception:
            continue
            
    return "\n\n".join(crawled_content)

# ==========================================
# 3. PDF REPORT ENGINE
# ==========================================

def create_pdf_report(filename, analysis_data, raw_metadata):
    """Generates a structured, professional corporate PDF document."""
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom aesthetic styling palettes
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=24, leading=28, textColor=colors.HexColor("#1A365D"), spaceAfter=12)
    h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontSize=16, leading=20, textColor=colors.HexColor("#2B6CB0"), spaceBefore=14, spaceAfter=8)
    body_style = ParagraphStyle('CustomBody', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#2D3748"))
    
    # Header Elements
    story.append(Paragraph(f"Corporate Research Intelligence Report", title_style))
    story.append(Paragraph(f"Target: {raw_metadata['name']} ({raw_metadata['url']})", body_style))
    story.append(Spacer(1, 15))
    
    # Metadata Overview Table Block
    meta_data = [
        [Paragraph("<b>Property</b>", body_style), Paragraph("<b>Value</b>", body_style)],
        [Paragraph("Company Name", body_style), Paragraph(raw_metadata['name'], body_style)],
        [Paragraph("Official Website", body_style), Paragraph(raw_metadata['url'], body_style)],
        [Paragraph("Contact / Location Details", body_style), Paragraph(raw_metadata['contact'], body_style)],
    ]
    t = Table(meta_data, colWidths=[150, 380])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Processing sections generated from Markdown markers
    sections = analysis_data.split('\n\n')
    for sec in sections:
        if sec.strip().startswith('**') or sec.strip().startswith('###') or sec.strip().startswith('##'):
            clean_header = sec.replace('**', '').replace('###', '').replace('##', '').strip()
            story.append(Paragraph(clean_header, h2_style))
        else:
            clean_text = sec.replace('**', '').replace('*', '').strip()
            if clean_text:
                story.append(Paragraph(clean_text, body_style))
                story.append(Spacer(1, 6))
                
    doc.build(story)

# ==========================================
# 4. DISCORD BOT WORKFLOW AUTOMATION
# ==========================================

def dispatch_to_discord(bot_token, channel_id, applicant_name, applicant_email, company_name, company_url, pdf_path):
    """Sends applicant information and attaches the generated PDF report to a Discord channel."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {bot_token}"}
    
    content_payload = (
        f"🚨 **New Research Report Generated** 🚨\n\n"
        f"**Applicant Name:** {applicant_name}\n"
        f"**Applicant Email:** {applicant_email}\n"
        f"**Company Researched:** {company_name}\n"
        f"**Company Website:** {company_url}\n"
    )
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {
                'file': (f"{company_name}_Report.pdf", f, 'application/pdf')
            }
            data = {
                'content': content_payload
            }
            res = requests.post(url, headers=headers, data=data, files=files, timeout=15)
            return res.status_code in [200, 201]
    except Exception as e:
        st.error(f"Discord Dispatch Error: {e}")
        return False

# ==========================================
# 5. STREAMLIT MODERN UX INTERFACE
# ==========================================

st.set_page_config(page_title="AI Company Research Assistant", page_icon="🤖", layout="wide")

# Persistent state mapping
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "report_markdown" not in st.session_state:
    st.session_state.report_markdown = ""
if "meta" not in st.session_state:
    st.session_state.meta = {}

# Sidebar Configuration Layout
with st.sidebar:
    st.title("Settings & Config")
    
    # Model Selection Capability
    model_choice = st.selectbox("Select AI Processing Model", [
        "openrouter/free", 
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free"
    ])
    
    st.markdown("---")
    st.subheader("Discord Integration Setup (Bonus)")
    app_name = st.text_input("Applicant Name", value="Devesh Joshi")
    app_email = st.text_input("Applicant Email Address", value="deveshjoshi177@gmail.com")
    bot_token = st.text_input("Discord Bot Token", type="password")
    chan_id = st.text_input("Discord Channel ID")

# Main Interface Screen
st.title("💬 Intelligent AI Research System")
st.write("Provide a target company name or explicit web URL to crawl pages, parse external public records, discover direct domain competitors, and generate professional intelligence summaries.")

# Single Chat-style execution box
input_query = st.text_input("Enter Company Name or Complete Website URL (e.g., 'Stripe' or 'https://tesla.com'):")

if st.button("Generate Intelligence Report", type="primary"):
    if not input_query.strip():
        st.warning("Please submit a valid identity parameter.")
    else:
        # Determine operational orientation routing
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
                    st.caption("Defaulting link structures due to standard matching drops.")
            
            # Step 2: Extracting Site Intel
            status.update(label=f"Crawling deep assets from {target_url}...")
            crawled_text = ""
            if target_url.startswith("http"):
                crawled_text = intelligent_crawl(target_url, max_pages=5)
            
            # Step 3: Fetch Competitor and Supplemental Signals
            status.update(label="Scanning public records for metadata and address maps...")
            meta_intel = search_public_intel(f"{target_name} headquarters contact address phone number")
            comp_intel = search_public_intel(f"{target_name} core direct market competitors and alternative alternatives")
            
            # Step 4: AI Synthesis Generation Prompting Engine
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
            (Explicitly identify and construct a list of top 3 competitors along with their respective websites)
            """
            
            analysis_output = ask_openrouter(model_choice, prompt)
            
            # Parsing location meta parameters out cleanly
            contact_info = "Not explicitly found in top layers"
            phone_match = re.search(r'\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', meta_intel)
            if phone_match:
                contact_info = phone_match.group(0)
                
            # Storing session boundaries
            st.session_state.meta = {
                "name": target_name,
                "url": target_url,
                "contact": contact_info
            }
            st.session_state.report_markdown = analysis_output
            st.session_state.analysis_complete = True
            status.update(label="Analysis Pipeline complete!", state="complete")

# Output Section Render Frame
if st.session_state.analysis_complete:
    st.markdown("---")
    st.subheader(f"📊 Market Analysis Output: {st.session_state.meta['name']}")
    st.markdown(st.session_state.report_markdown)
    
    # Local Generation Process Hooks for PDF Distribution Buildouts
    pdf_filename = "Intelligence_Report.pdf"
    create_pdf_report(pdf_filename, st.session_state.report_markdown, st.session_state.meta)
    
    # 1-Click Download Module Implementation requirement
    with open(pdf_filename, "rb") as pdf_file:
        st.download_button(
            label="📥 Download Professional PDF Report",
            data=pdf_file,
            file_name=f"{st.session_state.meta['name']}_Intelligence_Report.pdf",
            mime="application/pdf"
        )
        
    # Automatic Discord Workflow Trigger condition
    if bot_token and chan_id:
        with st.spinner("Automating Discord channel data synchronization dispatch..."):
            success = dispatch_to_discord(
                bot_token=bot_token,
                channel_id=chan_id,
                applicant_name=app_name,
                applicant_email=app_email,
                company_name=st.session_state.meta['name'],
                company_url=st.session_state.meta['url'],
                pdf_path=pdf_filename
            )
            if success:
                st.success("✅ Hackathon Automation Success: File data package routed to specified Discord channel seamlessly!")
            else:
                st.error("❌ Failed sending package payload parameters down to Discord API gateway endpoints.")