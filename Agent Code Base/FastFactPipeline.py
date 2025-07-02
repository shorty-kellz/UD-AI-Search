import os
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
import html2text

class FastFactProcessor:
    def __init__(self, input_folder="FastFacts", output_file="FastFact Library.json"):
        self.input_folder = Path(input_folder)
        self.output_file = output_file
        self.fast_facts = []
        
    def extract_title(self, content):
        """Extract the title from MIME headers - text between Subject: and Date:"""
        subject_match = re.search(r'Subject:\s*(.+?)\s+Date:', content, re.DOTALL)
        if subject_match:
            title = subject_match.group(1).strip()
            # Clean up any encoding artifacts
            title = re.sub(r'=\s*\n\s*', '', title)  # Remove line continuations
            title = re.sub(r'=\s*$', '', title)      # Remove trailing = signs
            return title
        return "Unknown Title"
    
    def extract_url(self, content):
        """Extract URL from Snapshot-Content-Location in MIME headers"""
        url_match = re.search(r'Snapshot-Content-Location:\s*(https?://[^\s]+)', content)
        if url_match:
            return url_match.group(1)
        return "https://www.mypcnow.org/fast-facts"
    
    def extract_fast_fact_number(self, content):
        """Extract the Fast Fact number from content"""
        match = re.search(r'Fast Fact Number:\s*(\d+)', content)
        if match:
            return match.group(1)
        return None
    
    def extract_authors(self, content):
        """Extract authors from content"""
        match = re.search(r'By:\s*(.+)', content)
        if match:
            return match.group(1).strip()
        return "Unknown Authors"
    
    def extract_categories(self, content):
        """Extract categories and convert to tags"""
        match = re.search(r'Categories:\s*(.+)', content)
        if match:
            categories_text = match.group(1).strip()
            # Split by comma and clean up
            categories = [cat.strip() for cat in categories_text.split(',')]
            # Clean up HTML entities and tags
            cleaned_categories = []
            for cat in categories:
                # Remove HTML tags
                cat = re.sub(r'<[^>]+>', '', cat)
                # Decode HTML entities
                cat = cat.replace('=3D', '=').replace('&lt;', '<').replace('&gt;', '>')
                # Remove encoded characters and equals signs
                cat = re.sub(r'=\s*\n\s*', '', cat)  # Remove soft line breaks
                cat = re.sub(r'=\s*$', '', cat)      # Remove trailing = signs
                cat = re.sub(r'=', '', cat)          # Remove all remaining = signs
                # Remove asterisks and other markdown artifacts
                cat = re.sub(r'^\*+\s*', '', cat)    # Remove leading asterisks
                cat = re.sub(r'\s*\*+$', '', cat)    # Remove trailing asterisks
                # Clean up extra whitespace
                cat = re.sub(r'\s+', ' ', cat).strip()
                if cat and cat not in cleaned_categories:
                    cleaned_categories.append(cat)
            return cleaned_categories
        return []
    
    def extract_published_date(self, content):
        """Extract published date"""
        match = re.search(r'Published On:\s*(.+)', content)
        if match:
            return match.group(1).strip()
        return "Unknown Date"
    
    def extract_summary(self, content):
        """Extract summary content from after published date to references from HTML section of MHTML"""
        # Find the HTML content section
        html_match = re.search(r'Content-Type: text/html.*?(?=Content-Type:|$)', content, re.DOTALL | re.IGNORECASE)
        if html_match:
            html_content = html_match.group(0)
            # Use BeautifulSoup to parse HTML
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
                # Remove equals signs and encoding artifacts
                summary_text = re.sub(r'=\s*\n\s*', '', summary_text)  # Remove soft line breaks
                summary_text = re.sub(r'=\s*$', '', summary_text)      # Remove trailing = signs
                summary_text = re.sub(r'=', '', summary_text)          # Remove all remaining = signs
                return summary_text
        return "Summary not available"
    
    def process_mhtml_file(self, file_path):
        """Process a single MHTML file and extract structured data"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract title from MIME headers
            title = self.extract_title(content)
            
            # Extract URL from MIME headers
            url = self.extract_url(content)
            
            # Extract summary from HTML content
            summary = self.extract_summary(content)
            
            # Extract tags from categories (using the same HTML content)
            html_match = re.search(r'Content-Type: text/html.*?(?=Content-Type:|$)', content, re.DOTALL | re.IGNORECASE)
            if html_match:
                html_content = html_match.group(0)
                h = html2text.HTML2Text()
                h.ignore_links = True
                h.ignore_images = True
                h.body_width = 0
                plain_text = h.handle(html_content)
                tags = self.extract_categories(plain_text)
            else:
                tags = []
            
            # Create structured data
            fast_fact_data = {
                "title": title,
                "summary": summary,
                "tags": tags,
                "url": url
            }
            
            return fast_fact_data
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return None
    
    def process_all_files(self):
        """Process all MHTML files in the input folder"""
        if not self.input_folder.exists():
            print(f"Input folder {self.input_folder} does not exist!")
            return
        
        mhtml_files = list(self.input_folder.glob("*.mhtml"))
        
        if not mhtml_files:
            print(f"No MHTML files found in {self.input_folder}")
            return
        
        print(f"Found {len(mhtml_files)} MHTML files to process...")
        
        for file_path in mhtml_files:
            print(f"Processing: {file_path.name}")
            fast_fact_data = self.process_mhtml_file(file_path)
            
            if fast_fact_data:
                self.fast_facts.append(fast_fact_data)
                print(f"  ✓ Extracted: {fast_fact_data['title']}")
            else:
                print(f"  ✗ Failed to process: {file_path.name}")
        
        print(f"\nSuccessfully processed {len(self.fast_facts)} files")
    
    def save_to_json(self):
        """Save the processed data to JSON file"""
        output_path = Path(self.output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.fast_facts, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved {len(self.fast_facts)} Fast Facts to {output_path}")
    
    def run(self):
        """Run the complete pipeline"""
        print("Starting Fast Fact Processing Pipeline...")
        print("=" * 50)
        
        self.process_all_files()
        self.save_to_json()
        
        print("\nPipeline completed successfully!")
        print(f"Output file: {self.output_file}")

def main():
    # Create processor instance
    processor = FastFactProcessor()
    
    # Run the pipeline
    processor.run()

if __name__ == "__main__":
    main() 