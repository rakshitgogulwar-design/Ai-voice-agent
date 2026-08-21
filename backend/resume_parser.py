"""
Resume Parser Module
Extracts structured information from uploaded resumes (PDF, DOCX, TXT).
"""

import re
import os
import tempfile
from typing import Dict, Any, List, Optional


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except ImportError:
        pass

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except ImportError:
        pass

    return ""


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        return ""
    except Exception:
        return ""


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from a TXT file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def extract_text(file_path: str, file_type: str) -> str:
    """Extract text based on file type."""
    file_type = file_type.lower()
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "docx":
        return extract_text_from_docx(file_path)
    elif file_type == "txt":
        return extract_text_from_txt(file_path)
    return ""


def sanitize_text(text: str) -> str:
    """Sanitize extracted resume text."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {3,}', '  ', text)
    # Remove non-printable characters
    text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
    return text.strip()


def detect_name(text: str) -> str:
    """Detect candidate name from resume text."""
    lines = text.strip().split('\n')
    # First non-empty line is often the name
    for line in lines[:5]:
        line = line.strip()
        if not line:
            continue
        # Skip lines that look like headers/contact info
        if any(kw in line.lower() for kw in ['resume', 'cv', 'curriculum', 'telephone', 'email', 'phone', 'address', 'linkedin', 'github']):
            continue
        if '@' in line or 'http' in line or re.match(r'^[\d\-\(\)\+\. ]+$', line):
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(w[0].isupper() if w else False for w in words):
            return line
    return ""


def detect_email(text: str) -> str:
    """Extract email address from resume text."""
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else ""


def detect_phone(text: str) -> str:
    """Extract phone number from resume text."""
    match = re.search(r'[\+]?[(]?\d{1,4}[)]?[-\s\./]?\d{1,4}[-\s\./]?\d{1,9}', text)
    return match.group(0) if match else ""


def detect_location(text: str) -> str:
    """Try to detect location from resume text."""
    location_patterns = [
        r'(?:Location|Address|City|Based in)[:\s]*([A-Z][a-zA-Z\s,]+(?:NY|CA|TX|FL|WA|IL|MA|CO|GA|NC|PA|OH|MI|VA|NJ|MD|OR|MN|WI|TN|AZ|UT|NV|IN|MO|CT|SC|AL|LA|KY|OK|KS|IA|AR|MS|NE|NM|HI|ID|NH|ME|MT|RI|DE|SD|ND|WV|VT|WY|AK|DC))',
        r'(?:San Francisco|New York|Los Angeles|Chicago|Seattle|Austin|Boston|Denver|Atlanta|Portland|Miami|Dallas|Houston|Phoenix|Philadelphia|San Diego|Minneapolis|Detroit|Nashville|Washington DC|Bay Area|Remote)',
    ]
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) if match.lastindex else match.group(0)
    return ""


def detect_sections(text: str) -> List[Dict[str, str]]:
    """Detect resume sections by common headers."""
    section_headers = [
        'summary', 'professional summary', 'objective', 'profile', 'about',
        'experience', 'work experience', 'employment history', 'professional experience',
        'education', 'academic background',
        'skills', 'technical skills', 'core competencies', 'technologies',
        'projects', 'key projects', 'notable projects',
        'certifications', 'licenses', 'credentials',
        'achievements', 'accomplishments', 'awards',
        'publications', 'research',
        'volunteer', 'volunteer experience',
        'languages', 'interests', 'hobbies',
        'references',
    ]

    lines = text.split('\n')
    sections = []
    current_header = None
    current_content = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_content.append("")
            continue

        # Check if this line is a section header
        is_header = False
        for header in section_headers:
            if stripped.lower().rstrip(':') == header or stripped.lower() == header + ':':
                is_header = True
                break
            # Also match if line is all uppercase and matches
            if stripped.upper().rstrip(':') == header.upper():
                is_header = True
                break

        if is_header:
            if current_header and current_content:
                sections.append({
                    "title": current_header,
                    "content": "\n".join(current_content).strip()
                })
            current_header = stripped.rstrip(':').strip()
            current_content = []
        else:
            current_content.append(stripped)

    if current_header and current_content:
        sections.append({
            "title": current_header,
            "content": "\n".join(current_content).strip()
        })

    return sections


def detect_skills(text: str) -> List[str]:
    """Detect skills and technologies from resume text."""
    common_skills = [
        'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'ruby', 'go', 'golang',
        'rust', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'sql', 'nosql',
        'react', 'angular', 'vue', 'vue.js', 'next.js', 'nextjs', 'node.js', 'nodejs',
        'django', 'flask', 'fastapi', 'spring', 'spring boot', 'rails', 'laravel',
        'express', 'express.js', 'graphql', 'rest', 'rest api', 'restful',
        'html', 'css', 'sass', 'scss', 'tailwind', 'bootstrap',
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb',
        'cassandra', 'sqlite', 'oracle', 'sql server',
        'aws', 'amazon web services', 'gcp', 'google cloud', 'azure', 'docker', 'kubernetes',
        'terraform', 'ansible', 'jenkins', 'ci/cd', 'github actions',
        'machine learning', 'deep learning', 'nlp', 'natural language processing',
        'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
        'git', 'github', 'gitlab', 'bitbucket',
        'agile', 'scrum', 'kanban', 'jira', 'confluence',
        'linux', 'unix', 'bash', 'shell scripting',
        'microservices', 'serverless', 'lambda', 'kafka', 'rabbitmq',
        'figma', 'sketch', 'adobe xd', 'photoshop', 'illustrator',
        'tableau', 'power bi', 'excel', 'google analytics',
        'blockchain', 'solidity', 'web3',
        'node', 'react native', 'flutter', 'ionic',
        'spring', 'hibernate', 'maven', 'gradle',
        'webpack', 'babel', 'vite', 'npm', 'yarn',
        'redis', 'memcached', 'nginx', 'apache',
        'prometheus', 'grafana', 'datadog', 'splunk',
    ]

    text_lower = text.lower()
    found = []
    for skill in common_skills:
        # Use word boundary matching
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            display = skill.title() if len(skill) <= 4 else skill
            if display not in found:
                found.append(display)
    return found


def detect_projects(text: str) -> List[Dict[str, str]]:
    """Detect projects from resume text."""
    projects = []
    # Look for project-like descriptions
    project_patterns = [
        r'(?:Project|Built|Developed|Created|Designed|Implemented|Launched)[:\s]*(.+?)(?:\n|$)',
    ]
    for pattern in project_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            desc = m.group(1).strip()
            if len(desc) > 10 and len(desc) < 300:
                projects.append({"name": desc[:80], "description": desc})
    return projects[:10]  # Limit to 10


def detect_achievements(text: str) -> List[str]:
    """Detect achievements and measurable results."""
    achievements = []
    achievement_patterns = [
        r'(?:Achieved|Accomplished|Increased|Reduced|Improved|Decreased|Saved|Generated|Delivered|Led|Managed|Scaled)[:\s]*(.+?)(?:\n|$)',
        r'(\d+%\s+(?:increase|reduction|improvement|growth|savings|efficiency|faster|slower|more|less))',
        r'(\$\d[\d,]*(?:\.\d+)?\s*(?:million|billion|thousand|k|m|b)?\s*(?:in|of|saved|revenue|budget)?)',
    ]
    for pattern in achievement_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            achievement = m.group(0).strip()
            if len(achievement) > 10 and achievement not in achievements:
                achievements.append(achievement)
    return achievements[:10]


def detect_education(text: str) -> List[Dict[str, str]]:
    """Detect education entries."""
    education = []
    edu_patterns = [
        r'(Bachelor|Master|PhD|Ph\.D|B\.S\.|M\.S\.|B\.A\.|M\.A\.|MBA|B\.Tech|M\.Tech|Associate)[^\.]*(?:in\s+)?([A-Za-z\s]+?)(?:,|\s+from\s+|\s+at\s+|\s*$)',
        r'((?:University|College|Institute|School)\s+of\s+[A-Za-z\s]+)',
    ]
    for pattern in edu_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            edu = m.group(0).strip()
            if len(edu) > 5:
                education.append({"degree": edu, "institution": ""})
    return education[:5]


def detect_certifications(text: str) -> List[str]:
    """Detect certifications."""
    certs = []
    cert_patterns = [
        r'(?:Certified|Certification|License)[:\s]*(.+?)(?:\n|$)',
        r'((?:AWS|Azure|GCP|Google|Cisco|Microsoft|Oracle|PMP|CISSP|CompTIA|Scrum Master|Certified)[^\.]{5,80})',
    ]
    for pattern in cert_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            cert = m.group(0).strip()
            if cert not in certs:
                certs.append(cert)
    return certs[:10]


def detect_job_titles(text: str) -> List[str]:
    """Detect job titles from resume text."""
    titles = []
    title_patterns = [
        r'(?:Senior|Junior|Lead|Principal|Staff|Head of|Director of|VP of|Chief|Associate|Assistant)?\s*(?:Software|Data|Cloud|DevOps|Site Reliability|Full[\s-]?Stack|Front[\s-]?End|Back[\s-]?End|Machine Learning|AI|ML|Product|Project|Program|Engineering|Systems|Network|Security|Quality|UX|UI|Backend|Frontend|Mobile|iOS|Android|Database|Solutions|Enterprise|Technical|IT|Operations|Research|Applied)\s*(?:Engineer|Developer|Architect|Manager|Analyst|Scientist|Designer|Consultant|Specialist|Director|Lead|Intern)',
    ]
    for pattern in title_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            title = m.group(0).strip()
            if title and title not in titles:
                titles.append(title)
    return titles[:8]


def detect_companies(text: str) -> List[str]:
    """Detect company names mentioned in the resume for context only."""
    companies = []
    company_patterns = [
        r'(?:at|@|for|from)\s+([A-Z][A-Za-z\.]+(?:\s+[A-Z][A-Za-z\.]+)?)',
    ]
    known_companies = [
        'Google', 'Amazon', 'Microsoft', 'Apple', 'Meta', 'Netflix', 'Tesla',
        'Uber', 'Airbnb', 'Stripe', 'Shopify', 'Salesforce', 'Adobe', 'Oracle',
        'IBM', 'Intel', 'Cisco', 'SAP', 'VMware', 'Snowflake', 'Databricks',
        'Palantir', 'Twitter', 'LinkedIn', 'Spotify', 'Slack', 'Dropbox',
        'Goldman Sachs', 'JPMorgan', 'Morgan Stanley', 'Deloitte', 'McKinsey',
        'Boston Consulting', 'Bain', 'Accenture', 'Capgemini',
    ]
    for company in known_companies:
        if re.search(r'\b' + re.escape(company) + r'\b', text, re.IGNORECASE):
            if company not in companies:
                companies.append(company)
    return companies


def parse_resume(file_path: str, file_type: str, filename: str = "") -> Dict[str, Any]:
    """
    Main resume parsing function.
    Extracts all relevant information from a resume file.
    """
    raw_text = extract_text(file_path, file_type)
    if not raw_text:
        return {
            "raw_text": "",
            "profile": {
                "name": "",
                "email": "",
                "phone": "",
                "location": "",
                "summary": "",
                "job_titles": [],
                "companies": [],
                "skills": [],
                "tools_and_tech": [],
                "projects": [],
                "achievements": [],
                "education": [],
                "certifications": [],
                "career_timeline": [],
                "measurable_results": [],
                "missing_or_unclear": ["Could not extract text from the uploaded file."],
                "sections": [],
            }
        }

    sanitized = sanitize_text(raw_text)
    sections = detect_sections(sanitized)

    # Extract summary from sections
    summary = ""
    for section in sections:
        if section["title"].lower() in ['summary', 'professional summary', 'objective', 'profile', 'about']:
            summary = section["content"]
            break

    # Detect skills and split into skills vs tools/tech
    all_skills = detect_skills(sanitized)
    tech_tools = ['python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'ruby', 'go',
                  'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'fastapi',
                  'postgresql', 'mysql', 'mongodb', 'redis', 'docker', 'kubernetes',
                  'aws', 'gcp', 'azure', 'terraform', 'jenkins', 'git',
                  'tensorflow', 'pytorch', 'pandas', 'numpy',
                  'linux', 'bash', 'nginx', 'kafka', 'graphql', 'rest api',
                  'webpack', 'vite', 'npm', 'figma', 'jira']

    skills = [s for s in all_skills if s.lower() not in [t.lower() for t in tech_tools]]
    tools = [s for s in all_skills if s.lower() in [t.lower() for t in tech_tools]]

    # Detect missing info
    missing = []
    if not summary:
        missing.append("No professional summary detected")
    if not detect_email(sanitized):
        missing.append("No email address found")
    if not detect_phone(sanitized):
        missing.append("No phone number found")
    if not detect_location(sanitized):
        missing.append("No location information found")

    profile = {
        "name": detect_name(sanitized),
        "email": detect_email(sanitized),
        "phone": detect_phone(sanitized),
        "location": detect_location(sanitized),
        "summary": summary,
        "job_titles": detect_job_titles(sanitized),
        "companies": detect_companies(sanitized),
        "skills": skills,
        "tools_and_tech": tools,
        "projects": detect_projects(sanitized),
        "achievements": detect_achievements(sanitized),
        "education": detect_education(sanitized),
        "certifications": detect_certifications(sanitized),
        "career_timeline": [],
        "measurable_results": [a for a in detect_achievements(sanitized) if any(c.isdigit() for c in a)],
        "missing_or_unclear": missing,
        "sections": sections,
    }

    return {
        "raw_text": sanitized,
        "profile": profile,
    }


def parse_resume_text(raw_text: str, filename: str = "resume.txt") -> Dict[str, Any]:
    """
    Parse resume from raw text (bypasses file extraction).
    Used for text-paste uploads and testing.
    """
    if not raw_text or not raw_text.strip():
        return {
            "raw_text": "",
            "profile": {
                "name": "", "email": "", "phone": "", "location": "",
                "summary": "", "job_titles": [], "companies": [],
                "skills": [], "tools_and_tech": [], "projects": [],
                "achievements": [], "education": [], "certifications": [],
                "career_timeline": [], "measurable_results": [],
                "missing_or_unclear": ["Empty resume text."], "sections": [],
            }
        }

    sanitized = sanitize_text(raw_text)
    sections = detect_sections(sanitized)

    summary = ""
    for section in sections:
        if section["title"].lower() in ['summary', 'professional summary', 'objective', 'profile', 'about']:
            summary = section["content"]
            break

    all_skills = detect_skills(sanitized)
    tech_tools_list = ['python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'ruby', 'go',
                  'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'fastapi',
                  'postgresql', 'mysql', 'mongodb', 'redis', 'docker', 'kubernetes',
                  'aws', 'gcp', 'azure', 'terraform', 'jenkins', 'git',
                  'tensorflow', 'pytorch', 'pandas', 'numpy',
                  'linux', 'bash', 'nginx', 'kafka', 'graphql', 'rest api']

    skills = [s for s in all_skills if s.lower() not in [t.lower() for t in tech_tools_list]]
    tools = [s for s in all_skills if s.lower() in [t.lower() for t in tech_tools_list]]

    missing = []
    if not summary:
        missing.append("No professional summary detected")
    if not detect_email(sanitized):
        missing.append("No email address found")
    if not detect_phone(sanitized):
        missing.append("No phone number found")
    if not detect_location(sanitized):
        missing.append("No location information found")

    profile = {
        "name": detect_name(sanitized),
        "email": detect_email(sanitized),
        "phone": detect_phone(sanitized),
        "location": detect_location(sanitized),
        "summary": summary,
        "job_titles": detect_job_titles(sanitized),
        "companies": detect_companies(sanitized),
        "skills": skills,
        "tools_and_tech": tools,
        "projects": detect_projects(sanitized),
        "achievements": detect_achievements(sanitized),
        "education": detect_education(sanitized),
        "certifications": detect_certifications(sanitized),
        "career_timeline": [],
        "measurable_results": [a for a in detect_achievements(sanitized) if any(c.isdigit() for c in a)],
        "missing_or_unclear": missing,
        "sections": sections,
    }

    return {
        "raw_text": sanitized,
        "profile": profile,
    }
