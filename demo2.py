import streamlit as st
import json
import os
import requests
from datetime import datetime as dt
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from collections import Counter
import re
import ssl
import socket
import time
import tempfile
import shutil
from pathlib import Path
import hashlib
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import google.generativeai as genai
from dotenv import load_dotenv
import serpapi
from Crawler import crawl_website
from icp import ICPChatbot
from seocheck import SEOAnalyzer

# Configure API keys
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAzz8WW4z6S9mETS7gLChmH5UkFlgrlL2o")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "e8ba07c3494f92a8c88f9a4c4a6fc70263b750c9c5697247e05c790535284384")

# Initialize APIs
genai.configure(api_key=GEMINI_API_KEY)
client = serpapi.Client(api_key=SERPAPI_API_KEY)

# Custom CSS for Astute AI theme
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load custom CSS
local_css("style.css")

def generate_seo_report(results):
    """Generate a comprehensive text report from analysis results"""
    report = []
    
    # General Information
    report.append("="*50)
    report.append("SEO ANALYSIS REPORT")
    report.append("="*50)
    report.append(f"\nURL: {results['general_info']['url']}")
    report.append(f"Date: {results['general_info']['date']}")
    report.append(f"User Agent: {results['general_info']['user_agent']}\n")

    # On-Page Factors
    report.append("\n" + "-"*50)
    report.append("ON-PAGE SEO FACTORS")
    report.append("-"*50)
    
    # Title analysis
    title = results['on_page']['title']
    report.append(f"\nTitle Tag: {title['text']}")
    report.append(f"Length: {title['length']} characters, {title['word_count']} words")
    if title['issues']:
        report.append("Issues:")
        for issue in title['issues']:
            report.append(f"  - {issue}")

    # Meta description analysis
    meta = results['on_page']['meta_description']
    report.append(f"\nMeta Description: {meta['text']}")
    report.append(f"Length: {meta['length']} characters, {meta['word_count']} words")
    if meta['issues']:
        report.append("Issues:")
        for issue in meta['issues']:
            report.append(f"  - {issue}")

    # Content analysis
    text = results['on_page']['text']
    report.append(f"\nText Content: {text['word_count']} words")
    if text['issues']:
        report.append("Issues:")
        for issue in text['issues']:
            report.append(f"  - {issue}")

    # Semantic Analysis
    report.append("\n" + "-"*50)
    report.append("SEMANTIC ANALYSIS")
    report.append("-"*50)
    
    sem = results['semantics']
    report.append("\nTop Keywords:")
    for kw in sem['top_keywords'][:5]:
        report.append(f"  - {kw['keyword']} (Count: {kw['count']}, Density: {kw['density']}%)")

    report.append(f"\nReadability Score: {sem['readability']['flesch_score']}")
    report.append(f"Readability Level: {sem['readability']['level']}")

    # Content Structure
    report.append("\n" + "-"*50)
    report.append("CONTENT STRUCTURE")
    report.append("-"*50)
    
    content = results['content']
    report.append("\nMost Common Words:")
    for word, count in list(content['word_frequencies'].items())[:10]:
        report.append(f"  - {word}: {count}")

    return "\n".join(report)

def extract_keywords_with_gemini(content, business_description):
    """Use Gemini to extract relevant keywords based on content and business context"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Analyze the following website content and business description to extract the most relevant keywords:
        
        BUSINESS DESCRIPTION:
        {business_description}
        
        WEBSITE CONTENT:
        {content}
        
        Return a JSON list of keywords in this format:
        {{
            "keywords": ["keyword1", "keyword2", "keyword3"]
        }}
        
        IMPORTANT: 
        - Only return valid JSON format
        - Do not include any additional text or markdown
        - Return between 5-15 most relevant keywords
        """
        
        response = model.generate_content(prompt)
        
        # Clean the response to extract just the JSON portion
        try:
            # Try to parse the entire response as JSON first
            response_json = json.loads(response.text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from within the response
            json_str = response.text.split('```json')[1].split('```')[0] if '```json' in response.text else response.text
            response_json = json.loads(json_str)
        
        # Ensure the response has the expected structure
        if 'keywords' not in response_json:
            response_json['keywords'] = []
            
        return response_json
        
    except Exception as e:
        st.error(f"Error extracting keywords: {str(e)}")
        return {"keywords": []}

def get_serp_analytics(keyword):
    """Get SERP analytics for a keyword using SERP API"""
    try:
        params = {
            "engine": "google_trends",
            "q": keyword,
            "api_key": SERPAPI_API_KEY,
            "data_type": "TIMESERIES"
        }
        results = client.search(params)
        return {
            "keyword": keyword,
            "search_volume": results.get("search_parameters", {}).get("search_volume", 0),
            "competition": results.get("competition", "Medium"),
            "timeline_data": results.get("timeline_data", [])
        }
    except Exception as e:
        st.error(f"Error getting SERP data: {str(e)}")
        return None

def visualize_keyword_trends(keyword_data):
    """Create visualizations for keyword trends"""
    try:
        if not keyword_data or not keyword_data.get('timeline_data'):
            return None, None
            
        # Create a DataFrame from the time series data
        df = pd.DataFrame({
            'date': [item['date'] for item in keyword_data['timeline_data']],
            'value': [item['values'][0]['extracted_value'] for item in keyword_data['timeline_data']]
        })
        
        # Line chart
        fig1 = px.line(df, x='date', y='value', title=f"Search Trend for '{keyword_data['keyword']}'")
        
        # Bar chart for monthly averages
        df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
        monthly_avg = df.groupby('month')['value'].mean().reset_index()
        monthly_avg['month'] = monthly_avg['month'].astype(str)
        fig2 = px.bar(monthly_avg, x='month', y='value', title=f"Monthly Average for '{keyword_data['keyword']}'")
        
        return fig1, fig2
    except Exception as e:
        st.error(f"Error visualizing trends: {str(e)}")
        return None, None

def generate_insightq_report(icp_data, seo_report_text, keywords_data):
    """Generate an InsightQ report combining ICP data, SEO analysis, and keyword research"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare keyword insights
        top_keywords = "\n".join([f"- {kw}" for kw in keywords_data.get('keywords', [])[:5]])
        
        prompt = f"""
        Create a comprehensive InsightQ report with these sections:
        
        1. BUSINESS OVERVIEW
        - Industry: {icp_data['form_data'].get('industry', 'N/A')}
        - Goals: {', '.join(icp_data['form_data'].get('main_goals', []))}
        - Unique Value: {icp_data['form_data'].get('unique_value', 'N/A')}
        
        2. SEO HEALTH ASSESSMENT
        {seo_report_text}
        
        3. KEYWORD RESEARCH INSIGHTS
        Top Keywords:
        {top_keywords}
        
        4. CONTENT STRATEGY
        - Suggest content topics based on keywords and business goals
        - Recommend content formats
        
        5. TECHNICAL IMPROVEMENTS
        - Prioritized fixes from SEO analysis
        
        Format with clear section headings and bullet points.
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        st.error(f"Error generating InsightQ report: {str(e)}")
        return None

# Initialize session state
if "start_crawling" not in st.session_state:
    st.session_state.start_crawling = False

if "crawled_links" not in st.session_state:
    st.session_state.crawled_links = []

if "selected_link" not in st.session_state:
    st.session_state.selected_link = None

if "icp_complete" not in st.session_state:
    st.session_state.icp_complete = False

if "icp_data" not in st.session_state:
    st.session_state.icp_data = None

if "seo_analysis_done" not in st.session_state:
    st.session_state.seo_analysis_done = False

if "report_generated" not in st.session_state:
    st.session_state.report_generated = False

if "report_data" not in st.session_state:
    st.session_state.report_data = None

if "seo_results" not in st.session_state:
    st.session_state.seo_results = None

if "report_text" not in st.session_state:
    st.session_state.report_text = None

if "insightq_report" not in st.session_state:
    st.session_state.insightq_report = None

if "keyword_data" not in st.session_state:
    st.session_state.keyword_data = None

if "serp_results" not in st.session_state:
    st.session_state.serp_results = None

# Landing Page
st.markdown("""
<div class="landing-container">
    <div class="landing-header">
        <h1 class="landing-title">Transform Your Data with <span class="logo-text">Astute AI</span></h1>
        <p class="landing-subtitle">Powerful insights, beautiful visualizations, and AI-driven analysis - all in one application.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Navigation sidebar
with st.sidebar:
    st.markdown("""
    <div class="sidebar-header">
        <h3>Navigation</h3>
    </div>
    """, unsafe_allow_html=True)
    
    nav_options = ["Home", "ICP Setup", "Website Analysis", "SEO Reports", "Keyword Research"]
    selected_nav = st.radio("", nav_options, label_visibility="collapsed")

# ICP Form
if not st.session_state.icp_complete:
    st.markdown("""
    <div class="section-header">
        <h2>First, let's understand your business</h2>
        <p>We'll ask a few questions to create your Ideal Customer Profile (ICP)</p>
    </div>
    """, unsafe_allow_html=True)
    
    chatbot = ICPChatbot()
    chatbot.render_form()
    
    if st.session_state.get('form_complete', False):
        filename, insights = chatbot.save_form_data()
        
        with open(filename, 'r') as f:
            st.session_state.icp_data = json.load(f)
        
        st.session_state.icp_complete = True
        st.rerun()

elif not st.session_state.start_crawling:
    if st.button("Let's Begin 🚀", key="begin_btn"):
        st.session_state.start_crawling = True
        st.rerun()

# Website Analysis
if st.session_state.start_crawling:
    st.markdown("""
    <div class="section-header">
        <h2>Website Analysis</h2>
        <p>Start by entering your website URL for comprehensive analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    icp_url = None
    if st.session_state.icp_data and 'form_data' in st.session_state.icp_data:
        icp_url = st.session_state.icp_data['form_data'].get('website_url', None)
    
    url = st.text_input(
        "Enter the main URL to analyze (e.g., https://example.com)",
        value=icp_url if icp_url else "",
        key="analysis_url"
    )

    if st.button("Start Analysis", key="analyze_btn"):
        if url:
            with st.spinner("Crawling website..."):
                crawled_links = crawl_website(url)
                st.session_state.crawled_links = crawled_links
                json_filename = "crawled_links.json"
                with open(json_filename, "w") as f:
                    json.dump(crawled_links, f, indent=4)

            st.success(f"Crawling completed! {len(crawled_links)} links found.")
            st.rerun()

# Analysis Options
if st.session_state.crawled_links:
    st.markdown("""
    <div class="section-header">
        <h2>Analysis Options</h2>
        <p>Select a page to analyze and generate reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.icp_data:
        with st.expander("View ICP Insights", expanded=True):
            st.subheader("Your Business Profile Insights")
            for i, insight in enumerate(st.session_state.icp_data.get('insights', []), 1):
                st.markdown(f"{i}. {insight}")
    
    selected_link = st.radio(
        "Select a page to analyze:",
        st.session_state.crawled_links,
        key="link_selection"
    )
    st.session_state.selected_link = selected_link

    if st.button("Run SEO Analysis", key="seo_btn"):
        if st.session_state.selected_link:
            with st.spinner("Analyzing SEO... This may take a moment"):
                try:
                    analyzer = SEOAnalyzer(st.session_state.selected_link)
                    results = analyzer.analyze()
                    st.session_state.seo_results = results
                    
                    report_text = generate_seo_report(results)
                    st.session_state.report_text = report_text
                    
                    domain = urlparse(st.session_state.selected_link).netloc
                    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"reports/{domain}_{timestamp}_report.txt"
                    
                    os.makedirs("reports", exist_ok=True)
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(report_text)

                    st.session_state.seo_analysis_done = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
        else:
            st.warning("Please select a link first")

# Display Results
if st.session_state.seo_analysis_done and st.session_state.seo_results:
    results = st.session_state.seo_results
    
    st.success(f"SEO Analysis for {st.session_state.selected_link}")
    
    if st.session_state.report_text:
        st.download_button(
            label="Download Text Report",
            data=st.session_state.report_text,
            file_name="seo_analysis_report.txt",
            mime="text/plain",
            key="download_report"
        )
    
    # Keyword Research Section
    if st.session_state.icp_data and st.button("Run Keyword Research", key="keyword_btn"):
        with st.spinner("Analyzing content and extracting keywords..."):
            try:
                # Get content from SEO results
                content = "\n".join([
                    results['on_page']['title']['text'],
                    results['on_page']['meta_description']['text'],
                    " ".join([kw['keyword'] for kw in results['semantics']['top_keywords']])
                ])
                
                business_desc = st.session_state.icp_data['form_data'].get('business_description', '')
                keyword_data = extract_keywords_with_gemini(content, business_desc)
                st.session_state.keyword_data = keyword_data
                
                # Get SERP analytics for top keywords
                serp_results = []
                for kw in keyword_data['keywords'][:3]:  # Limit to top 3 for demo
                    serp_data = get_serp_analytics(kw)
                    if serp_data:
                        serp_data['keyword'] = kw
                        serp_results.append(serp_data)
                
                st.session_state.serp_results = serp_results
                st.rerun()
                
            except Exception as e:
                st.error(f"Keyword research error: {str(e)}")

    # Display Keyword Research Results
    if st.session_state.keyword_data:
        st.markdown("""
        <div class="section-header">
            <h2>Keyword Research Results</h2>
            <p>Top keywords extracted from your content</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.keyword_data.get('keywords'):
            st.write("**Top Keywords:**")
            cols = st.columns(4)  # Creates 4 columns
            for i, keyword in enumerate(st.session_state.keyword_data['keywords']):
                if i >= 12:  # Limit to 12 keywords (3 rows of 4)
                    break
                with cols[i % 4]:  # Distributes keywords across columns
                    st.markdown(f"""
                    <div class="keyword-chip">
                        {keyword}
                    </div>
                    """, unsafe_allow_html=True)
            
            # SERP Analytics Visualization
            if st.session_state.serp_results:
                st.markdown("""
                <div class="section-header">
                    <h2>Keyword Trends Analysis</h2>
                    <p>Search volume and competition for your top keywords</p>
                </div>
                """, unsafe_allow_html=True)
                
                for result in st.session_state.serp_results:
                    st.markdown(f"""
                    <div class="keyword-header">
                        <h3>{result.get('keyword', 'Unknown')}</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display search volume and competition
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Monthly Search Volume", result.get('search_volume', 'N/A'))
                    with col2:
                        st.metric("Competition Level", result.get('competition', 'N/A'))
                    
                    # Visualizations
                    fig1, fig2 = visualize_keyword_trends(result)
                    if fig1 and fig2:
                        st.plotly_chart(fig1, use_container_width=True)
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    st.divider()
        else:
            st.warning("No keywords were extracted from the content")

    # InsightQ Report Generation
    if st.session_state.icp_data and st.button("Generate InsightQ Report", key="insightq_btn"):
        with st.spinner("Generating comprehensive InsightQ report..."):
            keyword_data = getattr(st.session_state, 'keyword_data', {'keywords': []})
            insightq_report = generate_insightq_report(
                st.session_state.icp_data,
                st.session_state.report_text,
                keyword_data
            )
            
            if insightq_report:
                st.session_state.insightq_report = insightq_report
                st.rerun()

    if st.session_state.insightq_report:
        st.markdown("""
        <div class="section-header">
            <h2>InsightQ Report</h2>
            <p>Comprehensive analysis combining ICP, SEO, and keyword data</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("View Full InsightQ Report", expanded=True):
            st.write(st.session_state.insightq_report)
        
        st.download_button(
            label="Download InsightQ Report",
            data=st.session_state.insightq_report,
            file_name="insightq_report.txt",
            mime="text/plain",
            key="download_insightq"
        )

    # SEO Analysis Display
    with st.expander("General Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Analysis Date", results['general_info']['date'])
            st.metric("User Agent", results['general_info']['user_agent'])
        with col2:
            st.metric("Page Load Time", f"{results['performance']['load_time']}s")
            st.metric("HTTP/2 Support", "Yes" if results['technical']['http2_support'] else "No")

    with st.expander("On-Page SEO Analysis"):
        on_page = results['on_page']
        
        st.subheader("Title Tag")
        col1, col2, col3 = st.columns([3,1,1])
        col1.write(f"**Text:** {on_page['title']['text']}")
        col2.metric("Length", f"{on_page['title']['length']} chars")
        col3.metric("Words", on_page['title']['word_count'])
        if on_page['title']['issues']:
            for issue in on_page['title']['issues']:
                st.error(issue)
                
        st.subheader("Meta Description")
        col1, col2, col3 = st.columns([3,1,1])
        col1.write(f"**Text:** {on_page['meta_description']['text']}")
        col2.metric("Length", f"{on_page['meta_description']['length']} chars")
        col3.metric("Words", on_page['meta_description']['word_count'])
        if on_page['meta_description']['issues']:
            for issue in on_page['meta_description']['issues']:
                st.error(issue)
                
        st.subheader("Content Analysis")
        col1, col2 = st.columns(2)
        col1.metric("Word Count", on_page['text']['word_count'])
        col2.metric("Recommended", "400+", delta=f"{on_page['text']['word_count']-400}")
        if on_page['text']['issues']:
            for issue in on_page['text']['issues']:
                st.error(issue)

    with st.expander("Technical SEO Analysis"):
        tech = results['technical']
        
        st.subheader("Technical Factors")
        cols = st.columns(4)
        cols[0].metric("Robots.txt", "✅" if tech['robots_txt'] else "❌")
        cols[1].metric("Sitemap.xml", "✅" if tech['sitemap_xml'] else "❌")
        cols[2].metric("Canonical", "✅" if tech['canonical']['present'] else "❌")
        cols[3].metric("HTML5", "✅" if tech['html5_doctype'] else "❌")
        
        st.subheader("Code Quality")
        cols = st.columns(3)
        cols[0].metric("Inline CSS", tech['css_js']['inline_styles'])
        cols[1].metric("Inline JS", tech['css_js']['inline_scripts'])
        cols[2].metric("External JS", tech['css_js']['external_scripts'])
        
        if tech['issues']:
            st.subheader("Technical Issues")
            for issue in tech['issues']:
                st.error(issue)

    with st.expander("Semantic Analysis"):
        sem = results['semantics']
        
        st.subheader("Top Keywords")
        keywords = sem['top_keywords'][:5]
        for kw in keywords:
            st.progress(kw['visibility']/100, f"{kw['keyword']} - {kw['count']}x ({kw['density']}%)")
        
        st.subheader("Readability")
        cols = st.columns(2)
        cols[0].metric("Flesch Score", sem['readability']['flesch_score'])
        cols[1].metric("Level", sem['readability']['level'])

    with st.expander("Content Structure"):
        content = results['content']
        
        st.subheader("Semantic Tags")
        cols = st.columns(3)
        cols[0].metric("Paragraphs", content['semantic_tags']['p'])
        cols[1].metric("Lists", content['semantic_tags']['ul'] + content['semantic_tags']['ol'])
        cols[2].metric("Blockquotes", content['semantic_tags']['blockquote'])
        
        st.subheader("HTML5 Elements")
        cols = st.columns(3)
        cols[0].metric("Articles", content['html5_elements']['article'])
        cols[1].metric("Sections", content['html5_elements']['section'])
        cols[2].metric("Asides", content['html5_elements']['aside'])
    
    if st.session_state.icp_data:
        with st.expander("Personalized Recommendations", expanded=True):
            st.subheader("Recommendations Based on Your ICP")
            icp_industry = st.session_state.icp_data['form_data'].get('industry', 'your industry')
            icp_goals = st.session_state.icp_data['form_data'].get('main_goals', [])
            
            if "Increase organic traffic" in icp_goals:
                st.markdown(f"**For increasing traffic in {icp_industry}:**")
                st.markdown("- Focus on long-tail keywords specific to your niche")
                st.markdown("- Create pillar content around your core services/products")
            
            if "Boost sales and conversions" in icp_goals:
                st.markdown("**For improving conversions:**")
                st.markdown("- Add clear call-to-actions on each page")
                st.markdown("- Include customer testimonials and case studies")

