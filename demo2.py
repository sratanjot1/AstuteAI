# demo.py (updated version)
import streamlit as st
import json
import os
import requests
import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from Crawler import crawl_website
from collections import Counter
import re
import ssl
import socket
import time
from seocheck import SEOAnalyzer 
from icp import ICPChatbot  # Import the ICP chatbot class

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


# Session state to manage login and crawling states
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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

if not st.session_state.logged_in:
    st.title("Client Login")
    username = st.text_input("Enter Username")
    email = st.text_input("Enter Email")
    password = st.text_input("Enter Password", type="password")

    if st.button("Submit"):
        if username and email and password:
            user_data = {"username": username, "email": email, "password": password}
            with open("users.json", "w") as f:
                json.dump(user_data, f, indent=4)

            st.session_state.logged_in = True
            st.rerun()

else:
    # Hide login title after successful login
    st.title("Welcome to AstuteAI 🎉")
    st.write("You have successfully logged in!")

    # Check if we need to run the ICP chatbot
    if not st.session_state.icp_complete:
        st.subheader("First, let's understand your business")
        st.write("We'll ask a few questions to create your Ideal Customer Profile (ICP)")
        
        # Initialize and run the ICP chatbot
        chatbot = ICPChatbot()
        chatbot.render_form()
        
        # Check if the ICP form is complete
        if st.session_state.get('form_complete', False):
            # Save the ICP data
            filename, insights = chatbot.save_form_data()
            
            # Load the saved ICP data
            with open(filename, 'r') as f:
                st.session_state.icp_data = json.load(f)
            
            st.session_state.icp_complete = True
            st.rerun()
    
    # After ICP is complete, show the "Let's Begin" button
    elif not st.session_state.start_crawling:
        if st.button("Let's Begin 🚀"):
            st.session_state.start_crawling = True
            st.rerun()

# Show the crawler after pressing "Let's Begin"
if st.session_state.start_crawling:
    st.title("Website Analysis")
    
    # Get the URL from ICP data if available
    icp_url = None
    if st.session_state.icp_data and 'form_data' in st.session_state.icp_data:
        icp_url = st.session_state.icp_data['form_data'].get('website_url', None)
    
    # URL input with prefilled value from ICP
    url = st.text_input(
        "Enter the main URL to analyze (e.g., https://example.com)",
        value=icp_url if icp_url else ""
    )

    if st.button("Start Analysis"):
        if url:
            # First crawl the website
            with st.spinner("Crawling website..."):
                crawled_links = crawl_website(url)
                st.session_state.crawled_links = crawled_links
                json_filename = "crawled_links.json"
                with open(json_filename, "w") as f:
                    json.dump(crawled_links, f, indent=4)

            st.success(f"Crawling completed! {len(crawled_links)} links found.")
            st.rerun()

# Show analysis options after crawling
if st.session_state.crawled_links:
    st.subheader("Analysis Options")
    
    # Show ICP insights if available
    if st.session_state.icp_data:
        with st.expander("View ICP Insights", expanded=True):
            st.subheader("Your Business Profile Insights")
            for i, insight in enumerate(st.session_state.icp_data.get('insights', []), 1):
                st.markdown(f"{i}. {insight}")
    
    # Show crawled links and analysis options
    selected_link = st.radio(
        "Select a page to analyze:",
        st.session_state.crawled_links,
        key="link_selection"
    )
    st.session_state.selected_link = selected_link

    if st.button("Run SEO Analysis"):
        if st.session_state.selected_link:
            with st.spinner("Analyzing SEO... This may take a moment"):
                try:
                    # Run SEO analysis
                    analyzer = SEOAnalyzer(st.session_state.selected_link)
                    results = analyzer.analyze()
                    
                    # Generate and save report
                    report_text = generate_seo_report(results)
                    domain = urlparse(st.session_state.selected_link).netloc
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"reports/{domain}_{timestamp}_report.txt"
                    
                    os.makedirs("reports", exist_ok=True)
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(report_text)

                    # Display results in expandable sections
                    st.success(f"SEO Analysis for {st.session_state.selected_link}")
                    
                    # General Information
                    with st.expander("General Information", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Analysis Date", results['general_info']['date'])
                            st.metric("User Agent", results['general_info']['user_agent'])
                        with col2:
                            st.metric("Page Load Time", f"{results['performance']['load_time']}s")
                            st.metric("HTTP/2 Support", "Yes" if results['technical']['http2_support'] else "No")

                    # On-Page SEO Factors
                    with st.expander("On-Page SEO Analysis"):
                        on_page = results['on_page']
                        
                        # Title Analysis
                        st.subheader("Title Tag")
                        col1, col2, col3 = st.columns([3,1,1])
                        col1.write(f"**Text:** {on_page['title']['text']}")
                        col2.metric("Length", f"{on_page['title']['length']} chars")
                        col3.metric("Words", on_page['title']['word_count'])
                        if on_page['title']['issues']:
                            for issue in on_page['title']['issues']:
                                st.error(issue)
                                
                        # Meta Description Analysis
                        st.subheader("Meta Description")
                        col1, col2, col3 = st.columns([3,1,1])
                        col1.write(f"**Text:** {on_page['meta_description']['text']}")
                        col2.metric("Length", f"{on_page['meta_description']['length']} chars")
                        col3.metric("Words", on_page['meta_description']['word_count'])
                        if on_page['meta_description']['issues']:
                            for issue in on_page['meta_description']['issues']:
                                st.error(issue)
                                
                        # Content Analysis
                        st.subheader("Content Analysis")
                        col1, col2 = st.columns(2)
                        col1.metric("Word Count", on_page['text']['word_count'])
                        col2.metric("Recommended", "400+", delta=f"{on_page['text']['word_count']-400}")
                        if on_page['text']['issues']:
                            for issue in on_page['text']['issues']:
                                st.error(issue)

                    # Technical SEO Factors
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

                    # Semantic Analysis
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

                    # Content Analysis
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
                        
                    # Add ICP context to recommendations if available
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
                            
                            # Add more personalized recommendations based on ICP data

                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
        else:
            st.warning("Please select a link first")

# Add a reset button at the bottom
if st.session_state.get('start_crawling', False):
    if st.button("Start New Analysis"):
        # Reset all states except login
        st.session_state.start_crawling = False
        st.session_state.crawled_links = []
        st.session_state.selected_link = None
        st.session_state.icp_complete = False
        st.session_state.icp_data = None
        st.rerun()