"""
FastFact Parser - Extracts structured data from MHTML files
Extracted from the existing FastFactPipeline.py
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import html2text
import quopri
import email.header

class FastFactParser:
    """Parser for FastFact MHTML files"""
    
    def __init__(self):
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
        self.html_converter.body_width = 0
    
    def parse_mhtml_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a single MHTML file and extract structured data"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract all components
            title = self.extract_title(content)
            url = self.extract_url(content)
            summary = self.extract_summary(content)
            fast_fact_number = self.extract_fast_fact_number(content, file_path)
            tags = self.extract_tags(content)
            
            # Create structured data
            fast_fact_data = {
                "title": title,
                "summary": summary,
                "tags": tags,
                "url": url,
                "fast_fact_number": fast_fact_number,
                "file_path": file_path
            }
            
            return fast_fact_data
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return None
    
    def extract_title(self, content: str) -> str:
        """Extract the title from MIME headers - text between Subject: and Date:"""
        subject_match = re.search(r'Subject:\s*(.+?)\s+Date:', content, re.DOTALL)
        if subject_match:
            title = subject_match.group(1).strip()
            
            # Decode MIME quoted-printable encoding
            title = self.decode_mime_string(title)
            
            # Clean up any encoding artifacts
            title = re.sub(r'=\s*\n\s*', '', title)  # Remove line continuations
            title = re.sub(r'=\s*$', '', title)      # Remove trailing = signs
            
            # Remove "FF #XXX" prefix if present
            title = re.sub(r'^FF #\d+\s*', '', title)
            
            # Remove " | Palliative Care Network of Wisconsin" suffix
            title = re.sub(r'\s*\|\s*Palliative Care Network of Wisconsin\s*$', '', title)
            
            return title.strip()
        return "Unknown Title"
    
    def decode_mime_string(self, text: str) -> str:
        """Decode MIME quoted-printable encoded string"""
        
        try:
            # First try: Use email.header.decode_header for complex MIME strings
            if '=?utf-8?Q?' in text:
                try:
                    decoded_parts = email.header.decode_header(text)
                    result = ''
                    for part, encoding in decoded_parts:
                        if isinstance(part, bytes):
                            if encoding:
                                result += part.decode(encoding, errors='ignore')
                            else:
                                result += part.decode('utf-8', errors='ignore')
                        else:
                            result += str(part)
                    return result
                except Exception as e:
                    pass  # Fall through to next method
            
            # Second try: Handle the =?utf-8?Q?...?= format manually
            if text.startswith('=?utf-8?Q?') and text.endswith('?='):
                # Extract the encoded part
                encoded_part = text[10:-2]  # Remove =?utf-8?Q? and ?=
                # Decode quoted-printable
                decoded = quopri.decodestring(encoded_part).decode('utf-8')
                return decoded
            else:
                # Try to decode any quoted-printable parts
                decoded = quopri.decodestring(text).decode('utf-8', errors='ignore')
                return decoded
        except Exception as e:
            return text
    
    def extract_url(self, content: str) -> str:
        """Extract URL from Snapshot-Content-Location in MIME headers"""
        url_match = re.search(r'Snapshot-Content-Location:\s*(https?://[^\s]+)', content)
        if url_match:
            return url_match.group(1)
        return "https://www.mypcnow.org/fast-facts"
    
    def extract_fast_fact_number(self, content: str, file_path: str = None) -> Optional[str]:
        """Extract the Fast Fact number from content, title, or URL"""
        
        # Method 1: Extract from filename first (most reliable)
        if file_path:
            filename = Path(file_path).name
            filename_match = re.search(r'FF\s*#\s*(\d+)', filename, re.IGNORECASE)
            if filename_match:
                print(f"    DEBUG: Found FF number via filename: {filename_match.group(1)}")
                return filename_match.group(1)
        
        # Method 2: Look for "Fast Fact Number:" in content (handle encoded version)
        # First try the raw pattern
        match = re.search(r'Fast Fact Number:\s*(\d+)', content)
        if match:
            print(f"    DEBUG: Found FF number via 'Fast Fact Number:' method: {match.group(1)}")
            return match.group(1)
        
        # Try to find encoded version in HTML content
        html_match = re.search(r'Content-Type: text/html.*?(?=Content-Type:|$)', content, re.DOTALL | re.IGNORECASE)
        if html_match:
            html_content = html_match.group(0)
            # Look for encoded Fast Fact Number pattern
            encoded_match = re.search(r'Fast Fact Number:=\s*\n\s*(\d+)', html_content)
            if encoded_match:
                print(f"    DEBUG: Found FF number via encoded HTML: {encoded_match.group(1)}")
                return encoded_match.group(1)
            
            # Also try to find it in the decoded HTML text
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
                html_text = soup.get_text()
                html_ff_match = re.search(r'Fast Fact Number:\s*(\d+)', html_text)
                if html_ff_match:
                    print(f"    DEBUG: Found FF number via decoded HTML: {html_ff_match.group(1)}")
                    return html_ff_match.group(1)
            except:
                pass
        
        # Method 3: Extract from title (look for "FF #XXX" pattern)
        title_match = re.search(r'Subject:\s*(.+?)\s+Date:', content, re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            # Try to decode MIME encoding first
            title = self.decode_mime_string(title)
            
            # Look for "FF #XXX" pattern in title
            title_ff_match = re.search(r'FF\s*#\s*(\d+)', title, re.IGNORECASE)
            if title_ff_match:
                print(f"    DEBUG: Found FF number via title FF pattern: {title_ff_match.group(1)}")
                return title_ff_match.group(1)
        
        # Method 4: Look for URL patterns in content
        url_match = re.search(r'fast-fact.*?(\d+)', content, re.IGNORECASE)
        if url_match:
            print(f"    DEBUG: Found FF number via URL pattern: {url_match.group(1)}")
            return url_match.group(1)
        
        # Method 5: Look for "Fast Fact #XXX" pattern in content
        ff_pattern_match = re.search(r'Fast Fact\s*#\s*(\d+)', content, re.IGNORECASE)
        if ff_pattern_match:
            print(f"    DEBUG: Found FF number via 'Fast Fact #' pattern: {ff_pattern_match.group(1)}")
            return ff_pattern_match.group(1)
        
        # Method 6: Last resort - look for numbers that appear to be FastFact numbers
        # Look for patterns like "FF #123" or "Fast Fact 123" in the first 1000 characters
        content_start = content[:1000]
        ff_matches = re.findall(r'(?:FF\s*#|Fast Fact\s*#?)\s*(\d+)', content_start, re.IGNORECASE)
        if ff_matches:
            print(f"    DEBUG: Found FF number via content pattern: {ff_matches[0]}")
            return ff_matches[0]
        
        # Method 7: Very last resort - look for standalone numbers that could be FF numbers
        # But be much more restrictive - only look for numbers that appear in specific contexts
        content_start = content[:1000]
        
        # Look for numbers that appear after "Fact" or in specific patterns
        fact_number_matches = re.findall(r'(?:Fact|FF)\s*#?\s*(\d{1,3})', content_start, re.IGNORECASE)
        if fact_number_matches:
            print(f"    DEBUG: Found FF number via fact pattern (last resort): {fact_number_matches[0]}")
            return fact_number_matches[0]
        
        # Look for numbers in meta tags or specific HTML contexts
        meta_matches = re.findall(r'content=3D"[^"]*?(\d{1,3})[^"]*?"', content_start)
        if meta_matches:
            # Filter to reasonable FF numbers
            for match in meta_matches:
                num = int(match)
                if 1 <= num <= 999:  # Reasonable FF number range
                    print(f"    DEBUG: Found FF number via meta tag (last resort): {match}")
                    return match
        
        print(f"    DEBUG: Could not extract FastFact number")
        return None
    
    def extract_tags(self, content: str) -> List[str]:
        """Extract categories and convert to tags from HTML format"""
        # Look for the categories section in HTML
        categories_match = re.search(r'Categories:.*?<a href=3D.*?</p>', content, re.DOTALL)
        if not categories_match:
            return []
        
        categories_html = categories_match.group(0)
        
        # Extract all category names from title attributes
        # Pattern: title=3D"Category Name"
        title_matches = re.findall(r'title=3D"([^"]+)"', categories_html)
        
        if not title_matches:
            # Fallback: try to extract from link text between > and <
            title_matches = re.findall(r'>([^<]+)</a>', categories_html)
        
        # Clean up the extracted categories
        cleaned_categories = []
        for category in title_matches:
            # Decode HTML entities
            category = category.replace('=3D', '=').replace('&lt;', '<').replace('&gt;', '>')
            # Remove encoded characters and equals signs
            category = re.sub(r'=\s*\n\s*', '', category)  # Remove soft line breaks
            category = re.sub(r'=\s*$', '', category)      # Remove trailing = signs
            category = re.sub(r'=', '', category)          # Remove all remaining = signs
            # Clean up extra whitespace
            category = re.sub(r'\s+', ' ', category).strip()
            if category and category not in cleaned_categories:
                cleaned_categories.append(category)
        
        return cleaned_categories
    
    def extract_summary(self, content: str) -> str:
        """Extract summary content from after published date to References section from HTML section of MHTML"""
        try:
            # Find the HTML content section
            html_match = re.search(r'Content-Type: text/html.*?(?=Content-Type:|$)', content, re.DOTALL | re.IGNORECASE)
            if not html_match:
                print("    DEBUG: No HTML content found")
                return "Summary not available"
            
            html_content = html_match.group(0)
            
            # Extract just the HTML part, not the MIME headers
            # Look for the actual HTML content after the MIME headers
            html_start = html_content.find('<!DOCTYPE') or html_content.find('<html') or html_content.find('<body')
            if html_start == -1:
                # Try to find any HTML tag
                html_start = html_content.find('<')
            
            if html_start != -1:
                html_content = html_content[html_start:]
            else:
                return "Summary not available"
            
            # Use BeautifulSoup to parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove navigation, sidebar, and footer elements
            for element in soup.find_all(['nav', 'aside', 'footer', 'header', 'script', 'style']):
                element.decompose()
            
            # Remove elements with common navigation classes
            for element in soup.find_all(class_=re.compile(r'(menu|nav|sidebar|footer|header|breadcrumb)', re.I)):
                element.decompose()
            
            # Remove common navigation and footer text elements
            for element in soup.find_all(text=re.compile(r'(Home|About|Contact|Privacy|Terms|Login|Register|Search)', re.I)):
                try:
                    if hasattr(element, 'parent') and element.parent:
                        # Skip if this element is part of a References section
                        parent_text = element.parent.get_text().lower()
                        if 'references' in parent_text:
                            continue
                        
                        # Skip if this element is in a content area (not navigation)
                        parent_classes = element.parent.get('class', [])
                        if any(content_class in str(parent_classes).lower() for content_class in 
                              ['content', 'main', 'article', 'post', 'entry']):
                            continue
                        
                        # Only remove if it's clearly navigation (has navigation-like context)
                        element_text = element.strip().lower()
                        if element_text in ['home', 'about', 'contact', 'privacy', 'terms', 'login', 'register', 'search']:
                            element.parent.decompose()
                except AttributeError:
                    # Skip elements without parent (like NavigableString objects)
                    continue
            
            text = soup.get_text('\n', strip=True)
            
            # Simplified endpoint detection: Only look for "References" section
            
            end_idx = -1
            end_marker = None
            
            # Method 1: Look for "References" section headers in structured HTML elements
            # This is the most reliable method since section headers are always in specific HTML tags
            for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                tag_text = tag.get_text().strip()
                # Check for exact matches of section headers
                if tag_text in ["References", "References:", "REFERENCES", "REFERENCES:"]:
                    tag_pos = text.find(tag_text)
                    if tag_pos != -1:
                        end_idx = tag_pos
                        end_marker = f"{tag_text.lower()} (html)"
                        print(f"    DEBUG: Found HTML section header: {tag_text} at position {tag_pos}")
                        break
                
                # Also check if any strong tags within this tag contain "References"
                strong_tags = tag.find_all('strong')
                for strong_tag in strong_tags:
                    strong_text = strong_tag.get_text().strip()
                    if strong_text in ["References", "References:", "REFERENCES", "REFERENCES:"]:
                        tag_pos = text.find(strong_text)
                        if tag_pos != -1:
                            end_idx = tag_pos
                            end_marker = f"{strong_text.lower()} (html direct)"
                            print(f"    DEBUG: Found HTML direct section header: {strong_text} at position {tag_pos}")
                            break
                if end_idx != -1:
                    break
            
            # Method 2: If no HTML section header found, use smart text search for "References"
            if end_idx == -1:
                print(f"    DEBUG: No HTML section headers found, trying text search for References...")
                
                # Find all occurrences of "References" (case insensitive)
                references_positions = []
                pos = 0
                while True:
                    pos = text.lower().find('references', pos)
                    if pos == -1:
                        break
                    references_positions.append(pos)
                    pos += 1
                
                # Check each position to see if it's a section header (not content text)
                for pos in references_positions:
                    # Get context around this position
                    context_before = text[max(0, pos-50):pos]
                    context_after = text[pos:min(len(text), pos+50)]
                    
                    # Skip if it's in the disclaimer context
                    if "consult other relevant and up-to-date experts" in context_before:
                        continue
                    
                    # Skip if it's in the middle of a sentence (like "references 2 and 3")
                    if context_before and context_before[-1] not in ['\n', ' ', '.', ':', ';']:
                        continue
                    
                    # Skip if it's followed by numbers or other content (like "references 2 and 3")
                    word_after = context_after.split()[0] if context_after.split() else ""
                    if word_after and word_after.isdigit():
                        continue
                    
                    # Check if it looks like a section header:
                    # - Starts with capital R
                    # - Followed by colon or newline
                    # - Not in the middle of content
                    if (text[pos] == 'R' and  # Must start with capital R
                        (pos + 10 >= len(text) or text[pos + 10] in ['\n', ' ', ':'] or 
                         context_after.startswith('References:') or context_after.startswith('References\n'))):
                        
                        end_idx = pos
                        end_marker = "references (text)"
                        print(f"    DEBUG: Found text-based References at position {pos}")
                        break
            
            # Method 3: Fallback - Look for "Resources" section if no "References" found
            if end_idx == -1:
                print(f"    DEBUG: No References found, trying fallback search for Resources...")
                
                # Look for "Resources" in HTML headers first
                for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    tag_text = tag.get_text().strip()
                    if tag_text.lower() in ["resources", "resources:", "resources", "resources:"]:
                        tag_pos = text.find(tag_text)
                        if tag_pos != -1:
                            # Verify this is not navigation
                            context_before = text[max(0, tag_pos-100):tag_pos]
                            if not any(nav_term in context_before.lower() for nav_term in 
                                     ['menu', 'nav', 'search', 'www.mypcnow.org', 'fusion-']):
                                end_idx = tag_pos
                                end_marker = f"{tag_text.lower()} (html fallback)"
                                print(f"    DEBUG: Found HTML Resources fallback: {tag_text} at position {tag_pos}")
                                break
                
                # Also check for nested Resources tags
                if end_idx == -1:
                    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                        strong_tags = tag.find_all('strong')
                        for strong_tag in strong_tags:
                            strong_text = strong_tag.get_text().strip()
                            if strong_text.lower() in ["resources", "resources:", "resources", "resources:"]:
                                tag_pos = text.find(strong_text)
                                if tag_pos != -1:
                                    # Verify this is not navigation
                                    context_before = text[max(0, tag_pos-100):tag_pos]
                                    if not any(nav_term in context_before.lower() for nav_term in 
                                             ['menu', 'nav', 'search', 'www.mypcnow.org', 'fusion-']):
                                        end_idx = tag_pos
                                        end_marker = f"{strong_text.lower()} (html nested fallback)"
                                        print(f"    DEBUG: Found HTML nested Resources fallback: {strong_text} at position {tag_pos}")
                                        break
                        if end_idx != -1:
                            break
                
                # If still no endpoint, try text-based Resources search
                if end_idx == -1:
                    resources_positions = []
                    pos = 0
                    while True:
                        pos = text.lower().find('resources', pos)
                        if pos == -1:
                            break
                        resources_positions.append(pos)
                        pos += 1
                    
                    for pos in resources_positions:
                        context_before = text[max(0, pos-100):pos]
                        context_after = text[pos:min(len(text), pos+50)]
                        
                        # Skip navigation-related resources
                        if any(nav_term in context_before.lower() for nav_term in 
                              ['menu', 'nav', 'search', 'www.mypcnow.org', 'fusion-']):
                            continue
                        
                        # Check if it looks like a content section header
                        if (text[pos] == 'R' and  # Must start with capital R
                            (pos + 10 >= len(text) or text[pos + 10] in ['\n', ' ', ':'] or 
                             context_after.startswith('Resources:') or context_after.startswith('Resources\n'))):
                            
                            end_idx = pos
                            end_marker = "resources (text fallback)"
                            print(f"    DEBUG: Found text-based Resources fallback at position {pos}")
                            break
            
            print(f"    DEBUG: Final endpoint: {end_marker} at position {end_idx}")
            
            # Find the start index for summary
            published_on_idx = text.find('Published On:')
            
            if published_on_idx != -1 and end_idx != -1 and published_on_idx < end_idx:
                # Start after the published date line
                after_published = text.find('\n', published_on_idx)
                
                # Check for MIME boundary to avoid CSS content
                mime_boundary = text.find('------MultipartBoundary')
                if mime_boundary != -1 and mime_boundary < end_idx:
                    end_idx = mime_boundary
                    end_marker = "mime boundary"
                    print(f"    DEBUG: Found MIME boundary at position {mime_boundary}, using as endpoint")
                
                summary_text = text[after_published:end_idx].strip()
                
                # Clean up whitespace and encoding artifacts
                summary_text = re.sub(r'\n+', ' ', summary_text)
                summary_text = re.sub(r'\s+', ' ', summary_text)
                
                # Enhanced MIME decoding - handle more patterns
                summary_text = re.sub(r'=\s*\n\s*', '', summary_text)  # Remove soft line breaks
                summary_text = re.sub(r'=\s*$', '', summary_text)      # Remove trailing = signs
                
                # Comprehensive MIME decoding - handle all patterns we're seeing
                # First, decode the most complex patterns (multi-byte sequences)
                summary_text = re.sub(r'=E2=80=9C', '"', summary_text)  # Left double quotation mark
                summary_text = re.sub(r'=E2=80=9D', '"', summary_text)  # Right double quotation mark
                summary_text = re.sub(r'=E2=80=99', "'", summary_text)  # Right single quotation mark
                summary_text = re.sub(r'=E2=80=98', "'", summary_text)  # Left single quotation mark
                summary_text = re.sub(r'=E2=80=93', '–', summary_text)  # En dash
                summary_text = re.sub(r'=E2=80=94', '—', summary_text)  # Em dash
                summary_text = re.sub(r'=E2=80=A6', '…', summary_text)  # Horizontal ellipsis
                
                # Then decode single-byte patterns
                summary_text = re.sub(r'=3D', '=', summary_text)       # Decode =3D to =
                summary_text = re.sub(r'=20', ' ', summary_text)       # Decode =20 to space
                summary_text = re.sub(r'=2E', '.', summary_text)       # Decode =2E to .
                summary_text = re.sub(r'=2C', ',', summary_text)       # Decode =2C to ,
                summary_text = re.sub(r'=27', "'", summary_text)       # Decode =27 to '
                summary_text = re.sub(r'=22', '"', summary_text)       # Decode =22 to "
                summary_text = re.sub(r'=28', '(', summary_text)       # Decode =28 to (
                summary_text = re.sub(r'=29', ')', summary_text)       # Decode =29 to )
                summary_text = re.sub(r'=3A', ':', summary_text)       # Decode =3A to :
                summary_text = re.sub(r'=3B', ';', summary_text)       # Decode =3B to ;
                summary_text = re.sub(r'=21', '!', summary_text)       # Decode =21 to !
                summary_text = re.sub(r'=3F', '?', summary_text)       # Decode =3F to ?
                summary_text = re.sub(r'=C2=A0', ' ', summary_text)     # Non-breaking space
                
                # Fix broken MIME patterns that are causing incomplete sentences
                summary_text = re.sub(r'&nb=\s*sp;', ' ', summary_text)  # Fix broken non-breaking space
                summary_text = re.sub(r'=\s*$', '', summary_text)        # Remove trailing = signs
                summary_text = re.sub(r'=\s*\n', '', summary_text)       # Remove = at line breaks
                summary_text = re.sub(r'=\s*', '', summary_text)         # Remove isolated = signs
                
                # HTML entity decoding
                summary_text = re.sub(r'&nbsp;', ' ', summary_text)     # Non-breaking space
                summary_text = re.sub(r'&amp;', '&', summary_text)      # Ampersand
                summary_text = re.sub(r'&lt;', '<', summary_text)       # Less than
                summary_text = re.sub(r'&gt;', '>', summary_text)       # Greater than
                summary_text = re.sub(r'&quot;', '"', summary_text)     # Quote
                summary_text = re.sub(r'&#39;', "'", summary_text)      # Apostrophe
                
                # Remove date from the beginning
                summary_text = re.sub(r'^[A-Z][a-z]+ \d{1,2}, \d{4}\s*', '', summary_text)
                summary_text = re.sub(r'^[A-Z][a-z]+ \d{1,2} \d{4}\s*', '', summary_text)
                summary_text = re.sub(r'^[A-Z][a-z]+ \d{1,2},? \d{4}\s*', '', summary_text)
                
                # Remove common navigation and footer text patterns
                summary_text = re.sub(r'(Home|About|Contact|Privacy|Terms|Login|Register|Search).*?', '', summary_text, flags=re.I)
                
                # Enhanced HTML tag removal - handle broken MIME HTML tags
                summary_text = re.sub(r'<=\s*\n\s*[^>]*>', '', summary_text)  # Remove broken MIME HTML tags like <=\n/p>
                summary_text = re.sub(r'<[^>]+>', '', summary_text)     # Remove any remaining HTML tags
                summary_text = re.sub(r'&[a-zA-Z0-9#]+;', '', summary_text)  # Remove any remaining HTML entities
                
                # Remove excessive whitespace and normalize
                summary_text = re.sub(r'\s+', ' ', summary_text).strip()
                
                # Final cleanup of any remaining encoding artifacts
                summary_text = re.sub(r'=\s*$', '', summary_text)
                summary_text = re.sub(r'=\s*\n', '', summary_text)
                summary_text = re.sub(r'=\s*', '', summary_text)
                
                # Fix sentence endings that were broken by MIME encoding
                summary_text = re.sub(r'\s+([.!?])\s*$', r'\1', summary_text)  # Clean up sentence endings
                summary_text = re.sub(r'\s+([.!?])\s+', r'\1 ', summary_text)  # Fix sentence endings with spaces
                
                # Additional cleanup for common MIME artifacts
                summary_text = re.sub(r'\s+=\s+', ' ', summary_text)  # Remove isolated = signs with spaces
                summary_text = re.sub(r'=\s*([A-Z0-9]{2})', r'\1', summary_text)  # Fix broken MIME sequences
                
                return summary_text.strip()
            else:
                return "Summary not available"
        except Exception as e:
            return "Summary not available"
    
    def process_all_files(self, input_folder: str) -> List[Dict[str, Any]]:
        """Process all MHTML files in the input folder"""
        input_path = Path(input_folder)
        
        if not input_path.exists():
            print(f"Input folder {input_path} does not exist!")
            return []
        
        mhtml_files = list(input_path.glob("*.mhtml"))
        
        if not mhtml_files:
            print(f"No MHTML files found in {input_path}")
            return []
        
        print(f"Found {len(mhtml_files)} MHTML files to process...")
        
        fast_facts = []
        failed_files = []
        
        for file_path in mhtml_files:
            print(f"Processing: {file_path.name}")
            try:
                fast_fact_data = self.parse_mhtml_file(str(file_path))
                
                if fast_fact_data:
                    fast_facts.append(fast_fact_data)
                    print(f"  ✓ Extracted: {fast_fact_data['title']}")
                else:
                    failed_files.append((file_path.name, "parse_mhtml_file returned None"))
                    print(f"  ✗ Failed to parse: {file_path.name}")
            except Exception as e:
                failed_files.append((file_path.name, str(e)))
                print(f"  ✗ Exception processing {file_path.name}: {e}")
        
        print(f"\nSuccessfully processed {len(fast_facts)} files")
        
        if failed_files:
            print(f"\nFailed to process {len(failed_files)} files:")
            for filename, error in failed_files:
                print(f"  - {filename}: {error}")
        
        return fast_facts 