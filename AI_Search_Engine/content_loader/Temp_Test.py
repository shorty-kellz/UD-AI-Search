"""
Temporary script to compare stored summaries with raw content
to identify formatting issues and improvements.
"""

import sys
import os
from pathlib import Path
import re
from bs4 import BeautifulSoup

# Add the backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, '..', 'backend')
sys.path.insert(0, backend_dir)

from database import get_connection

def get_stored_summaries():
    """Get all stored summaries from the database"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, summary 
            FROM content_master 
            ORDER BY id
        """)
        
        results = cursor.fetchall()
    
    return results

def extract_raw_summary(file_path):
    """Extract summary from raw MHTML file using current parser logic"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Use the same logic as the parser
        html_match = re.search(r'Content-Type: text/html.*?(?=Content-Type:|$)', content, re.DOTALL | re.IGNORECASE)
        if html_match:
            html_content = html_match.group(0)
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text('\n', strip=True)
            
            # Find the start and end indices for summary
            published_on_idx = text.find('Published On:')
            references_idx = text.lower().find('references')
            
            if published_on_idx != -1 and references_idx != -1 and published_on_idx < references_idx:
                # Start after the published date line
                after_published = text.find('\n', published_on_idx)
                summary_text = text[after_published:references_idx].strip()
                
                # Clean up whitespace and encoding artifacts
                summary_text = re.sub(r'\n+', ' ', summary_text)
                summary_text = re.sub(r'\s+', ' ', summary_text)
                summary_text = re.sub(r'=\s*\n\s*', '', summary_text)
                summary_text = re.sub(r'=\s*$', '', summary_text)
                summary_text = re.sub(r'=', '', summary_text)
                
                # Remove date from the beginning
                summary_text = re.sub(r'^[A-Z][a-z]+ \d{1,2}, \d{4}\s*', '', summary_text)
                summary_text = re.sub(r'^[A-Z][a-z]+ \d{1,2} \d{4}\s*', '', summary_text)
                summary_text = re.sub(r'^[A-Z][a-z]+ \d{1,2},? \d{4}\s*', '', summary_text)
                
                return summary_text.strip()
        
        return "Summary not available"
    except Exception as e:
        return f"Error reading file: {e}"

def analyze_parsing_endpoint(file_path, stored_summary):
    """Analyze where the parsing stopped for incomplete sentences"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Use the same logic as the parser
        html_match = re.search(r'Content-Type: text/html.*?(?=Content-Type:|$)', content, re.DOTALL | re.IGNORECASE)
        if html_match:
            html_content = html_match.group(0)
            
            # Extract just the HTML part, not the MIME headers
            html_start = html_content.find('<!DOCTYPE') or html_content.find('<html') or html_content.find('<body')
            if html_start == -1:
                html_start = html_content.find('<')
            
            if html_start != -1:
                html_content = html_content[html_start:]
            
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text('\n', strip=True)
            
            # Find the start and end indices for summary
            published_on_idx = text.find('Published On:')
            references_idx = text.lower().find('references')
            resources_idx = text.lower().find('resources')
            
            # Use the first ending marker found
            end_idx = -1
            end_marker = None
            if references_idx != -1 and resources_idx != -1:
                if references_idx < resources_idx:
                    end_idx = references_idx
                    end_marker = "references"
                else:
                    end_idx = resources_idx
                    end_marker = "resources"
            elif references_idx != -1:
                end_idx = references_idx
                end_marker = "references"
            elif resources_idx != -1:
                end_idx = resources_idx
                end_marker = "resources"
            
            if published_on_idx != -1 and end_idx != -1 and published_on_idx < end_idx:
                # Get the context around the endpoint
                context_start = max(0, end_idx - 100)
                context_end = min(len(text), end_idx + 100)
                context = text[context_start:context_end]
                
                return {
                    'end_marker': end_marker,
                    'end_position': end_idx,
                    'context_before': text[max(0, end_idx-50):end_idx],
                    'context_after': text[end_idx:min(len(text), end_idx+50)],
                    'full_context': context
                }
        
        return None
    except Exception as e:
        return f"Error analyzing file: {e}"

def analyze_summary_quality():
    """Analyze the quality of stored summaries vs raw content"""
    print("ANALYZING SUMMARY QUALITY")
    print("=" * 80)
    
    stored_data = get_stored_summaries()
    total_entries = len(stored_data)
    
    print(f"Analyzing all {total_entries} entries in the database...")
    
    issues_found = []
    improvements_suggested = []
    summary_lengths = []
    entries_with_issues = 0
    
    # Analyze each entry
    for i, (db_id, title, stored_summary) in enumerate(stored_data, 1):
        print(f"\n{i}. ID: {db_id} - {title}")
        print("-" * 60)
        
        summary_length = len(stored_summary)
        summary_lengths.append(summary_length)
        print(f"Stored Summary Length: {summary_length} chars")
        
        # Check for common issues
        issues = []
        
        # Check for encoding artifacts
        if '=3D' in stored_summary or '=20' in stored_summary or '=2E' in stored_summary:
            issues.append("Contains MIME encoding artifacts")
        
        # Check for excessive whitespace
        if re.search(r'\s{3,}', stored_summary):
            issues.append("Contains excessive whitespace")
        
        # Check for HTML tags
        if '<' in stored_summary and '>' in stored_summary:
            issues.append("Contains HTML tags")
        
        # Check for very short summaries
        if summary_length < 50:
            issues.append("Very short summary")
        
        # Check for incomplete sentences
        incomplete_sentence_info = None
        if stored_summary and not stored_summary.endswith(('.', '!', '?')):
            issues.append("May end with incomplete sentence")
            # Get the last chunk of words for analysis
            words = stored_summary.split()
            last_chunk = ' '.join(words[-10:]) if len(words) >= 10 else stored_summary
            incomplete_sentence_info = {
                'last_chunk': last_chunk,
                'summary_length': summary_length,
                'last_char': stored_summary[-1] if stored_summary else '',
                'word_count': len(words)
            }
        
        # Check for "Summary not available"
        if stored_summary == "Summary not available":
            issues.append("No summary extracted")
        
        if issues:
            entries_with_issues += 1
            print(f"Issues found: {', '.join(issues)}")
            issues_found.extend(issues)
            
            # Show sample of stored summary
            print(f"Stored Summary (first 300 chars):")
            print(f"   {stored_summary[:300]}...")
            
            # Show detailed info for incomplete sentences
            if incomplete_sentence_info:
                print(f"Incomplete sentence details:")
                print(f"   • Last 10 words: '{incomplete_sentence_info['last_chunk']}'")
                print(f"   • Summary length: {incomplete_sentence_info['summary_length']} chars")
                print(f"   • Word count: {incomplete_sentence_info['word_count']} words")
                print(f"   • Last character: '{incomplete_sentence_info['last_char']}'")
                
                # Try to find the file and analyze the endpoint
                try:
                    # Look for the file in the fast_facts_raw directory
                    fast_facts_dir = Path(__file__).parent.parent / "data" / "fast_facts_raw"
                    if fast_facts_dir.exists():
                        # Try to find the file by title
                        for mhtml_file in fast_facts_dir.glob("*.mhtml"):
                            if title.lower() in mhtml_file.name.lower() or mhtml_file.name.lower() in title.lower():
                                print(f"   • Found matching file: {mhtml_file.name}")
                                endpoint_info = analyze_parsing_endpoint(str(mhtml_file), stored_summary)
                                if endpoint_info:
                                    print(f"   • Endpoint detected: '{endpoint_info['end_marker']}' at position {endpoint_info['end_position']}")
                                    print(f"   • Context before endpoint: '...{endpoint_info['context_before'][-50:]}'")
                                    print(f"   • Context after endpoint: '{endpoint_info['context_after'][:50]}...'")
                                else:
                                    print(f"   • Could not analyze endpoint detection")
                                break
                        else:
                            print(f"   • Could not find matching MHTML file")
                    else:
                        print(f"   • Fast facts directory not found")
                except Exception as e:
                    print(f"   • Error analyzing endpoint: {e}")
                
                print(f"   • Note: File path not available for endpoint analysis")
            
            # Suggest improvements
            if "Contains MIME encoding artifacts" in issues:
                improvements_suggested.append("Improve MIME decoding in summary extraction")
            if "Contains excessive whitespace" in issues:
                improvements_suggested.append("Better whitespace normalization")
            if "Contains HTML tags" in issues:
                improvements_suggested.append("Better HTML tag removal")
            if "No summary extracted" in issues:
                improvements_suggested.append("Fix summary extraction for problematic files")
        else:
            print("✅ No issues found")
            # Show a sample anyway
            print(f"Sample (first 200 chars):")
            print(f"   {stored_summary[:200]}...")
    
    # Summary of findings
    print(f"\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    print(f"Total entries analyzed: {total_entries}")
    print(f"Entries with issues: {entries_with_issues}")
    print(f"Entries without issues: {total_entries - entries_with_issues}")
    print(f"Success rate: {((total_entries - entries_with_issues) / total_entries * 100):.1f}%")
    
    if issues_found:
        print(f"\nTotal issues found: {len(issues_found)}")
        issue_counts = {}
        for issue in issues_found:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        print("\nIssue breakdown:")
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_entries) * 100
            print(f"   • {issue}: {count} occurrences ({percentage:.1f}%)")
        
        print(f"\nSuggested improvements:")
        unique_improvements = list(set(improvements_suggested))
        for improvement in unique_improvements:
            print(f"   • {improvement}")
        
        # Show list of problematic entries
        print(f"\n" + "=" * 80)
        print("PROBLEMATIC ENTRIES DETAIL")
        print("=" * 80)
        
        # Re-analyze to show problematic entries
        problematic_entries = []
        for i, (db_id, title, stored_summary) in enumerate(stored_data, 1):
            issues = []
            
            # Check for common issues
            if '=3D' in stored_summary or '=20' in stored_summary or '=2E' in stored_summary:
                issues.append("Contains MIME encoding artifacts")
            if re.search(r'\s{3,}', stored_summary):
                issues.append("Contains excessive whitespace")
            if '<' in stored_summary and '>' in stored_summary:
                issues.append("Contains HTML tags")
            if len(stored_summary) < 50:
                issues.append("Very short summary")
            if stored_summary and not stored_summary.endswith(('.', '!', '?')):
                issues.append("May end with incomplete sentence")
            if stored_summary == "Summary not available":
                issues.append("No summary extracted")
            
            if issues:
                problematic_entries.append({
                    'id': db_id,
                    'title': title,
                    'issues': issues,
                    'summary_length': len(stored_summary),
                    'last_chars': stored_summary[-50:] if stored_summary else ''
                })
        
        print(f"Found {len(problematic_entries)} problematic entries:")
        for entry in problematic_entries:
            print(f"\nID: {entry['id']} - {entry['title']}")
            print(f"   Issues: {', '.join(entry['issues'])}")
            print(f"   Summary length: {entry['summary_length']} chars")
            print(f"   Ends with: '{entry['last_chars']}'")
    else:
        print("No major issues found in the analyzed summaries")
    
    print(f"\nSummary statistics:")
    print(f"   • Analyzed {total_entries} summaries")
    print(f"   • Average stored summary length: {sum(summary_lengths) / len(summary_lengths):.0f} chars")
    print(f"   • Shortest summary: {min(summary_lengths)} chars")
    print(f"   • Longest summary: {max(summary_lengths)} chars")
    print(f"   • Median summary length: {sorted(summary_lengths)[len(summary_lengths)//2]} chars")
    
    # Length distribution
    short_count = sum(1 for length in summary_lengths if length < 100)
    medium_count = sum(1 for length in summary_lengths if 100 <= length <= 1000)
    long_count = sum(1 for length in summary_lengths if length > 1000)
    
    print(f"\nLength distribution:")
    print(f"   • Short (< 100 chars): {short_count} entries ({short_count/total_entries*100:.1f}%)")
    print(f"   • Medium (100-1000 chars): {medium_count} entries ({medium_count/total_entries*100:.1f}%)")
    print(f"   • Long (> 1000 chars): {long_count} entries ({long_count/total_entries*100:.1f}%)")

def test_endpoint_detection(file_path):
    """Test endpoint detection on a specific file"""
    print(f"Testing endpoint detection on: {file_path}")
    print("=" * 60)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Use the same logic as the parser
        html_match = re.search(r'Content-Type: text/html.*?(?=Content-Type:|$)', content, re.DOTALL | re.IGNORECASE)
        if html_match:
            html_content = html_match.group(0)
            
            # Extract just the HTML part, not the MIME headers
            html_start = html_content.find('<!DOCTYPE') or html_content.find('<html') or html_content.find('<body')
            if html_start == -1:
                html_start = html_content.find('<')
            
            if html_start != -1:
                html_content = html_content[html_start:]
            
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text('\n', strip=True)
            
            print(f"Text length: {len(text)}")
            
            # Test the endpoint detection logic
            end_idx = -1
            end_marker = None
            
            # Look for "References" or "Resources" in bold text (b, strong tags)
            print("\n1. Checking bold text:")
            for bold in soup.find_all(['b', 'strong']):
                bold_text = bold.get_text().strip()
                print(f"   Found bold: '{bold_text}'")
                if bold_text == "References" or bold_text == "References:":
                    bold_pos = text.find(bold_text)
                    print(f"   -> References found at position {bold_pos}")
                    if bold_pos != -1 and (end_idx == -1 or bold_pos < end_idx):
                        end_idx = bold_pos
                        end_marker = "References (bold)"
                        break
                elif bold_text == "Resources" or bold_text == "Resources:":
                    bold_pos = text.find(bold_text)
                    print(f"   -> Resources found at position {bold_pos}")
                    if bold_pos != -1 and (end_idx == -1 or bold_pos < end_idx):
                        end_idx = bold_pos
                        end_marker = "Resources (bold)"
                        break
            
            # Check paragraph tags
            if end_idx == -1:
                print("\n2. Checking paragraph tags:")
                for p_tag in soup.find_all('p'):
                    p_text = p_tag.get_text().strip()
                    clean_p_text = re.sub(r'\s+', ' ', p_text).strip()
                    if clean_p_text in ["References", "References:"]:
                        p_pos = text.find(clean_p_text)
                        print(f"   Found paragraph: '{clean_p_text}' at position {p_pos}")
                        if p_pos != -1 and (end_idx == -1 or p_pos < end_idx):
                            end_idx = p_pos
                            end_marker = "References (paragraph)"
                            break
                    elif clean_p_text in ["Resources", "Resources:"]:
                        p_pos = text.find(clean_p_text)
                        print(f"   Found paragraph: '{clean_p_text}' at position {p_pos}")
                        if p_pos != -1 and (end_idx == -1 or p_pos < end_idx):
                            end_idx = p_pos
                            end_marker = "Resources (paragraph)"
                            break
            
            # Check heading tags
            if end_idx == -1:
                print("\n3. Checking heading tags:")
                for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    for heading in soup.find_all(heading_tag):
                        heading_text = heading.get_text().strip()
                        if heading_text == "References" or heading_text == "References:":
                            heading_pos = text.find(heading_text)
                            print(f"   Found heading ({heading_tag}): '{heading_text}' at position {heading_pos}")
                            if heading_pos != -1 and (end_idx == -1 or heading_pos < end_idx):
                                end_idx = heading_pos
                                end_marker = "References (heading)"
                                break
                        elif heading_text == "Resources" or heading_text == "Resources:":
                            heading_pos = text.find(heading_text)
                            print(f"   Found heading ({heading_tag}): '{heading_text}' at position {heading_pos}")
                            if heading_pos != -1 and (end_idx == -1 or heading_pos < end_idx):
                                end_idx = heading_pos
                                end_marker = "Resources (heading)"
                                break
            
            # Check div/span elements
            if end_idx == -1:
                print("\n4. Checking div/span elements:")
                for element in soup.find_all(['div', 'span']):
                    element_text = element.get_text().strip()
                    if element_text == "References" or element_text == "References:":
                        element_pos = text.find(element_text)
                        print(f"   Found div/span: '{element_text}' at position {element_pos}")
                        if element_pos != -1 and (end_idx == -1 or element_pos < end_idx):
                            end_idx = element_pos
                            end_marker = "References (div/span)"
                            break
                    elif element_text == "Resources" or element_text == "Resources:":
                        element_pos = text.find(element_text)
                        print(f"   Found div/span: '{element_text}' at position {element_pos}")
                        if element_pos != -1 and (end_idx == -1 or element_pos < end_idx):
                            end_idx = element_pos
                            end_marker = "Resources (div/span)"
                            break
            
            # Smart fallback
            if end_idx == -1:
                print("\n5. Checking simple text search:")
                references_idx = text.lower().find('references')
                resources_idx = text.lower().find('resources')
                
                print(f"   Simple 'references' found at: {references_idx}")
                print(f"   Simple 'resources' found at: {resources_idx}")
                
                if references_idx != -1:
                    context_before = text[max(0, references_idx-100):references_idx]
                    print(f"   Context before 'references': '...{context_before[-50:]}'")
                    if "consult other relevant and up-to-date experts" not in context_before:
                        end_idx = references_idx
                        end_marker = "references (simple)"
                        print(f"   -> Using simple references at position {references_idx}")
                    else:
                        print(f"   -> Skipping 'references' due to disclaimer context")
                
                if resources_idx != -1 and (end_idx == -1 or resources_idx < end_idx):
                    context_before = text[max(0, resources_idx-100):resources_idx]
                    print(f"   Context before 'resources': '...{context_before[-50:]}'")
                    if "consult other relevant and up-to-date experts" not in context_before:
                        end_idx = resources_idx
                        end_marker = "resources (simple)"
                        print(f"   -> Using simple resources at position {resources_idx}")
                    else:
                        print(f"   -> Skipping 'resources' due to disclaimer context")
            
            print(f"\nFinal result: {end_marker} at position {end_idx}")
            
            if end_idx != -1:
                # Show context around the endpoint
                context_start = max(0, end_idx - 50)
                context_end = min(len(text), end_idx + 50)
                print(f"\nContext around endpoint:")
                print(f"Before: '...{text[context_start:end_idx]}'")
                print(f"Endpoint: '{text[end_idx:end_idx+20]}...'")
                print(f"After: '{text[end_idx:context_end]}...'")
                
                # Test the actual summary extraction
                print(f"\nTesting summary extraction:")
                published_on_idx = text.find('Published On:')
                print(f"Published On found at: {published_on_idx}")
                
                if published_on_idx != -1 and end_idx != -1 and published_on_idx < end_idx:
                    # Start after the published date line
                    after_published = text.find('\n', published_on_idx)
                    summary_text = text[after_published:end_idx].strip()
                    
                    print(f"Summary length: {len(summary_text)}")
                    print(f"Summary ends with: '{summary_text[-50:]}'")
                    
                    # Check if it ends with a complete sentence
                    if summary_text and not summary_text.endswith(('.', '!', '?')):
                        print(f"❌ Summary ends with incomplete sentence")
                        # Find the last complete sentence
                        last_period = summary_text.rfind('.')
                        last_exclamation = summary_text.rfind('!')
                        last_question = summary_text.rfind('?')
                        last_sentence_end = max(last_period, last_exclamation, last_question)
                        
                        if last_sentence_end > 0:
                            complete_summary = summary_text[:last_sentence_end + 1]
                            print(f"Suggested complete summary ends: '{complete_summary[-50:]}'")
                        else:
                            print(f"No complete sentence found in summary")
                    else:
                        print(f"✅ Summary ends with complete sentence")
                else:
                    print(f"❌ Cannot extract summary - missing Published On or endpoint")
            
            return end_marker, end_idx
        
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

if __name__ == "__main__":
    # Test on a specific file
    test_file = "data/fast_facts_raw/FF #82 Medicare Hospice Benefit - Part 1_ Eligibility and Treatment Plan _ Palliative Care Network of Wisconsin.mhtml"
    if os.path.exists(test_file):
        print("=" * 80)
        print("RUNNING SPECIFIC ENDPOINT DETECTION TEST")
        print("=" * 80)
        test_endpoint_detection(test_file)
        print("\n" + "=" * 80)
        print("RUNNING FULL ANALYSIS")
        print("=" * 80)
        analyze_summary_quality()
    else:
        print(f"Test file not found: {test_file}")
        print("Running full analysis instead...")
        analyze_summary_quality() 