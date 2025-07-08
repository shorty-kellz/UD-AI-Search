"""
Simple Streamlit UI for AI Search Engine
"""

import streamlit as st
import requests
import json
from typing import Dict, Any
import re
from datetime import datetime
import uuid

# Configuration
BACKEND_URL = "http://localhost:8001"

def main():
    st.set_page_config(
        page_title="AI Search Engine",
        page_icon="🔍",
        layout="wide"
    )
    
    # Hide Streamlit elements
    hide_st_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """
    st.markdown(hide_st_style, unsafe_allow_html=True)
    
    # Create a header row with title and refresh button
    col1, col2, col3 = st.columns([4, 1, 1])
    
    with col1:
        st.title("ClinCore AI")
    
    with col3:
        if st.button("🔄 Refresh", key="refresh_button", use_container_width=True):
            # Clear all session state including the question
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            # Force a complete page refresh
            st.rerun()
    
    # Initialize session state for storing results
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'is_searching' not in st.session_state:
        st.session_state.is_searching = False
    if 'selected_question_id' not in st.session_state:
        st.session_state.selected_question_id = None
    if 'current_result_id' not in st.session_state:
        st.session_state.current_result_id = None
    
    # Get test questions from database
    test_questions = get_test_questions_from_db()
    
    # Question type and role selection on same line
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Option to use test questions or freeform
        question_type = st.radio(
            "Choose question type:",
            ["Test Question", "Freeform Question"],
            horizontal=True
        )
    
    with col2:
        # SME User Type dropdown
        if 'sme_user_type' not in st.session_state:
            st.session_state.sme_user_type = "Nurse"
        
        st.selectbox(
            "Choose what your role is:",
            ["Nurse", "Doctor", "Chaplain", "Doula"],
            index=["Nurse", "Doctor", "Chaplain", "Doula"].index(st.session_state.sme_user_type),
            key="sme_user_type"
        )
    
    if question_type == "Test Question":
        if test_questions:
            # Create options with both text and ID
            question_options = [q['question_text'] for q in test_questions]
            question_ids = [q['question_id'] for q in test_questions]
            
            # Dropdown for test questions
            selected_index = st.selectbox(
                "Select a test question:",
                options=range(len(question_options)),
                format_func=lambda x: question_options[x],
                index=0,
                help="Choose from predefined test questions"
            )
            
            question = question_options[selected_index]
            st.session_state.selected_question_id = question_ids[selected_index]
        else:
            st.warning("No test questions found in database. Please run the test questions ingestion pipeline first.")
            question = ""
            st.session_state.selected_question_id = None
    else:
        # Freeform question input
        question = st.text_input(
            "Enter your clinical question:",
            value="",
            key="question_input",
            help="Type your own clinical question"
        )
        st.session_state.selected_question_id = None  # No ID for freeform questions
    
    # Search button
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if question.strip():
            st.session_state.is_searching = True
            st.session_state.search_results = None
            
            # Process the search
            results = process_search(question.strip())
            st.session_state.search_results = results
            st.session_state.is_searching = False
            
            # Rerun to display results
            st.rerun()
        else:
            st.warning("Please enter a question before searching.")
    
    # Divider
    st.markdown("---")
    
    # Display loading state
    if st.session_state.is_searching:
        with st.spinner("Searching for answers..."):
            st.info("Processing your question through our AI agents...")
    
    # Display results in two-column layout
    if st.session_state.search_results:
        display_results_with_feedback(st.session_state.search_results)

def process_search(question: str) -> Dict[str, Any]:
    """Send question to backend and get results"""
    try:
        st.info(f"Sending question to backend: {question}")
        
        # Make request to backend
        response = requests.post(
            f"{BACKEND_URL}/query",
            params={"query": question, "user": "default"},
            timeout=60  # 60 second timeout for long responses
        )
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            st.error(f"Backend error: {response.status_code} - {response.text}")
            return {"success": False, "error": f"Backend error: {response.status_code}"}
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend server. Please make sure the backend is running on localhost:8001")
        return {"success": False, "error": "Backend connection failed"}
    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out. The search is taking longer than expected.")
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        st.error(f"❌ Error processing search: {str(e)}")
        return {"success": False, "error": str(e)}

def display_results(results: Dict[str, Any]):
    """Display search results"""
    st.markdown("---")
    st.markdown("### Search Results")
    
    # Check for errors in the response
    if results.get('error'):
        st.error(f"❌ Search failed: {results.get('error')}")
        return
    
    # Get the results from the correct field
    agent_results = results.get('results', {})
    active_agents = results.get('active_agents', [])
    
    if not agent_results:
        st.warning("⚠️ No responses received from agents")
        return
    
    # Display each agent's response
    for i, (agent_type, response) in enumerate(agent_results.items(), 1):
        success = response.get('success', False)
        recommendations = response.get('recommendations', '')
        error = response.get('error', '')
        
        # Create expandable section for each agent with numbered title
        with st.expander(f"{i}. {agent_type.title()} Response", expanded=True):
            if success:
                if recommendations:
                    # Parse and display JSON results
                    formatted_results = parse_json_results(recommendations)
                    st.markdown(formatted_results, unsafe_allow_html=True)
                else:
                    st.info("No specific recommendations provided by this agent.")
            else:
                st.error(f"Agent error: {error}")
            
            # Show metadata if available
            if response.get('usage_metrics'):
                st.caption(f"Usage: {response['usage_metrics']}")
    
    # Show overall status
    st.success(f"✅ Search completed successfully with {len(agent_results)} agent responses")

def display_results_with_feedback(results: Dict[str, Any]):
    """Display search results with SME feedback inputs in two-column layout"""
    st.markdown("---")
    st.markdown("### Search Results")
    
    # Check for errors in the response
    if results.get('error'):
        st.error(f"❌ Search failed: {results.get('error')}")
        return
    
    # Get the results from the correct field
    agent_results = results.get('results', {})
    active_agents = results.get('active_agents', [])
    
    if not agent_results:
        st.warning("⚠️ No responses received from agents")
        return
    
    # Display each agent's response with feedback
    for agent_type, response in agent_results.items():
        success = response.get('success', False)
        recommendations = response.get('recommendations', '')
        error = response.get('error', '')
        
        # Create expandable section for each agent
        with st.expander(f"{agent_type.title()} Response", expanded=True):
            if success:
                if recommendations:
                    # Parse and display JSON results with feedback
                    display_json_results_with_feedback(recommendations)
                else:
                    st.info("No specific recommendations provided by this agent.")
            else:
                st.error(f"Agent error: {error}")
            
            # Show metadata if available
            if response.get('usage_metrics'):
                st.caption(f"Usage: {response['usage_metrics']}")

def display_json_results_with_feedback(response_text: str):
    """Display JSON results with SME feedback inputs in two-column layout"""
    import json
    import re
    
    # Find JSON array in the response text
    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
    if not json_match:
        st.markdown("**Raw Response:**")
        st.text(response_text)
        return
    
    try:
        # Parse the JSON array
        json_str = json_match.group(0)
        results = json.loads(json_str)
        
        if not isinstance(results, list):
            st.markdown("**Raw Response:**")
            st.text(response_text)
            return
        
        # Display each result with feedback
        for i, result in enumerate(results, 1):
            title = result.get('title', 'N/A')
            explanation = result.get('explanation', 'N/A')
            matching_elements = result.get('matching_elements', 'N/A')
            url = result.get('url', 'N/A')
            relevance_score = result.get('relevance_score', 'N/A')
            
            # Create two-column layout for each result
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Display result content
                st.markdown(f"**Result #{i}**")
                st.markdown(f"**Title:** {title}")
                st.markdown(f"**Explanation:** {explanation}")
                st.markdown(f"**Matching Elements:** {matching_elements}")
                
                # Create clickable URL if it's a valid URL
                if url != 'N/A' and url.startswith('http'):
                    url_display = f"[{url}]({url})"
                else:
                    url_display = url
                st.markdown(f"**URL:** {url_display}")
                st.markdown(f"**Relevance Score:** {relevance_score}")
            
            with col2:
                # Initialize session state for this result if not exists
                result_key = f"result_{i}_feedback"
                if result_key not in st.session_state:
                    st.session_state[result_key] = {
                        'is_relevant_sme': None,  # Changed to None for radio button
                        'relevance_score_sme': 50,
                        'ideal_rank_sme': i
                    }
                
                # Row 1: Is Relevant radio buttons (forced selection)
                st.session_state[result_key]['is_relevant_sme'] = st.radio(
                    "Is Relevant",
                    options=["Yes", "No"],
                    index=None if st.session_state[result_key]['is_relevant_sme'] is None else (0 if st.session_state[result_key]['is_relevant_sme'] else 1),
                    horizontal=True,
                    key=f"relevant_{i}"
                )
                
                # Row 2: Relevance Score input with label
                st.session_state[result_key]['relevance_score_sme'] = st.number_input(
                    "Relevance Score",
                    min_value=0,
                    max_value=100,
                    value=st.session_state[result_key]['relevance_score_sme'],
                    step=5,
                    key=f"score_{i}"
                )
                
                # Row 3: Ideal Rank input with label
                st.session_state[result_key]['ideal_rank_sme'] = st.number_input(
                    "Ideal Rank",
                    min_value=1,
                    max_value=len(results),
                    value=st.session_state[result_key]['ideal_rank_sme'],
                    key=f"rank_{i}"
                )
            
            # Add divider after each result (outside the columns for better alignment)
            st.markdown("---")
        
        # Add submit button at the bottom center
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Submit Results", type="primary", use_container_width=True):
                # Validate that all required fields are filled
                all_valid = True
                missing_fields = []
                
                for i, result in enumerate(results, 1):
                    result_key = f"result_{i}_feedback"
                    feedback = st.session_state.get(result_key, {})
                    
                    # Check if "Is Relevant" is selected
                    if feedback.get('is_relevant_sme') is None:
                        all_valid = False
                        missing_fields.append(f"Result #{i}: Is Relevant selection")
                    
                    # Check if relevance score is filled (should always have a default value)
                    if feedback.get('relevance_score_sme') is None:
                        all_valid = False
                        missing_fields.append(f"Result #{i}: Relevance Score")
                    
                    # Check if ideal rank is filled (should always have a default value)
                    if feedback.get('ideal_rank_sme') is None:
                        all_valid = False
                        missing_fields.append(f"Result #{i}: Ideal Rank")
                
                if all_valid:
                    # Save data to database (placeholder method)
                    if save_feedback_to_database(results, st.session_state):
                        st.success("Results were submitted")
                        # Clear all session state and refresh to initial state
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        st.rerun()
                else:
                    st.error("❌ Please fill in all required fields before submitting:")
                    for field in missing_fields:
                        st.error(f"  • {field}")
        
    except json.JSONDecodeError:
        st.markdown("**Raw Response:**")
        st.text(response_text)
    


def format_agent_response(response_text: str) -> str:
    """Format agent response into structured result blocks"""
    if not response_text:
        return response_text
    
    # Try to parse the response into structured result blocks
    result_blocks = parse_response_into_blocks(response_text)
    
    if result_blocks:
        return format_result_blocks(result_blocks)
    else:
        # Fallback to original formatting if parsing fails
        return format_fallback_response(response_text)

def parse_response_into_blocks(response_text: str) -> list:
    """Parse response text into structured result blocks"""
    blocks = []
    current_block = {}
    
    lines = response_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Look for field patterns
        if ':' in line and len(line.split(':', 1)) >= 2:
            field, value = line.split(':', 1)
            field = field.strip().lower()
            value = value.strip()
            
            if field in ['title', 'explanation', 'matching elements', 'url', 'relevance score']:
                current_block[field] = value
            elif field in ['result', 'article', 'fast fact'] and value.isdigit():
                # New result block starting
                if current_block:
                    blocks.append(current_block)
                current_block = {'result_number': value}
    
    # Add the last block
    if current_block:
        blocks.append(current_block)
    
    # If no structured blocks found, try to create them from the text
    if not blocks:
        blocks = create_blocks_from_text(response_text)
    
    return blocks

def create_blocks_from_text(text: str) -> list:
    """Create result blocks from unstructured text"""
    # Preprocess: remove everything before the first numbered result
    lines = text.split('\n')
    start_index = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('#### ') and any(char.isdigit() for char in line):
            start_index = i
            break
    
    # Use only the text from the first numbered result onwards
    text = '\n'.join(lines[start_index:])
    
    blocks = []
    
    # Look for Fast Fact results specifically
    lines = text.split('\n')
    current_block = {}
    in_fast_fact = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this is a Fast Fact result (starts with #### and number)
        if line.startswith('#### ') and any(char.isdigit() for char in line):
            # Save previous block if it exists
            if current_block and current_block.get('title'):
                blocks.append(current_block)
            
            # Start new block
            current_block = {
                'result_number': str(len(blocks) + 1),
                'title': '',
                'explanation': '',
                'matching elements': '',
                'url': '',
                'relevance score': ''
            }
            in_fast_fact = True
            
            # Extract title from the line
            title = line.replace('#### ', '').strip()
            current_block['title'] = title
            
        elif in_fast_fact and line.startswith('- '):
            # Parse field information from the dash line
            dash_content = line[2:]  # Remove the "- " prefix
            
            # Extract all fields from this line
            if 'Explanation:' in dash_content:
                explanation = dash_content.split('Explanation:', 1)[1].split('- Matching Elements:', 1)[0].strip()
                current_block['explanation'] = explanation
            
            if 'Matching Elements:' in dash_content:
                matching_start = dash_content.find('Matching Elements:')
                matching_end = dash_content.find('- URL:', matching_start)
                if matching_end == -1:
                    matching_end = dash_content.find('- Relevance Score:', matching_start)
                if matching_end == -1:
                    matching_end = len(dash_content)
                
                matching = dash_content[matching_start + len('Matching Elements:'):matching_end].strip()
                current_block['matching elements'] = matching
            
            if 'URL:' in dash_content:
                url_start = dash_content.find('URL:')
                url_end = dash_content.find('- Relevance Score:', url_start)
                if url_end == -1:
                    url_end = len(dash_content)
                
                url = dash_content[url_start + len('URL:'):url_end].strip()
                current_block['url'] = url
            
            if 'Relevance Score:' in dash_content:
                score = dash_content.split('Relevance Score:', 1)[1].strip()
                current_block['relevance score'] = score
    
    # Add the last block
    if current_block and current_block.get('title'):
        blocks.append(current_block)
    
    # If no Fast Fact blocks found, try alternative parsing
    if not blocks:
        blocks = parse_alternative_format(text)
    
    # Filter out only the "Response:" block, keep everything else
    filtered_blocks = []
    for block in blocks:
        title = block.get('title', '').lower()
        if not (title.startswith('response:') or 'you are a clinical assistant' in title):
            filtered_blocks.append(block)
    
    return filtered_blocks

def is_response_block(title: str) -> bool:
    """Check if a block is a response block that should be skipped"""
    title_lower = title.lower()
    skip_patterns = [
        'response:',
        'you are a clinical assistant',
        'clinical question:',
        'relevant fast facts:',
        'note:'
    ]
    return any(pattern in title_lower for pattern in skip_patterns)

def parse_alternative_format(text: str) -> list:
    """Parse alternative response formats"""
    blocks = []
    
    # Look for patterns like "1. Title - Explanation"
    pattern = r'(\d+)\.\s+(.*?)\s+-\s+Explanation:\s+(.*?)(?=\d+\.|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    
    for i, (num, title, explanation) in enumerate(matches, 1):
        block = {
            'result_number': str(i),
            'title': title.strip(),
            'explanation': explanation.strip(),
            'matching elements': 'N/A',
            'url': 'N/A',
            'relevance score': 'N/A'
        }
        blocks.append(block)
    
    return blocks

def split_by_title_patterns(text: str) -> list:
    """Split text by looking for title patterns"""
    sections = []
    current_section = []
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line looks like a title (starts with common patterns)
        if (line.startswith('**') and line.endswith('**') or
            line.isupper() or
            line.startswith('Title:') or
            line.startswith('Fast Fact') or
            line.startswith('Article') or
            (len(line) < 100 and not line.startswith('http'))):
            
            # Start new section
            if current_section:
                sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    
    # Add the last section
    if current_section:
        sections.append('\n'.join(current_section))
    
    return sections

def create_artificial_splits(text: str) -> list:
    """Create artificial splits when no clear structure is found"""
    # Split by sentences or paragraphs
    sentences = text.split('. ')
    sections = []
    
    # Group sentences into sections
    current_section = []
    for sentence in sentences:
        current_section.append(sentence)
        
        # Create a new section every 3-5 sentences
        if len(current_section) >= 4:
            sections.append('. '.join(current_section))
            current_section = []
    
    # Add remaining sentences
    if current_section:
        sections.append('. '.join(current_section))
    
    return sections

def extract_first_line_as_title(section: str) -> str:
    """Extract the first meaningful line as a title"""
    lines = section.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('http') and len(line) < 200:
            return line
    return 'N/A'

def extract_explanation_from_section(section: str) -> str:
    """Extract explanation from section content"""
    lines = section.split('\n')
    content_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('Title:') and not line.startswith('http'):
            content_lines.append(line)
    
    return ' '.join(content_lines) if content_lines else 'N/A'



def extract_field(text: str, field_name: str) -> str:
    """Extract field value from text"""
    lines = text.split('\n')
    for line in lines:
        if line.lower().startswith(f'{field_name}:'):
            return line.split(':', 1)[1].strip() if ':' in line else ''
    return ''

def format_result_blocks(blocks: list) -> str:
    """Format result blocks with the specified structure"""
    formatted_blocks = []
    import re

    for i, block in enumerate(blocks, 1):
        result_number = block.get('result_number', str(i))
        # Remove markdown headings from title
        title = re.sub(r'^#+\s*', '', block.get('title', 'N/A')).strip()
        explanation = block.get('explanation', 'N/A')
        matching_elements = block.get('matching elements', 'N/A')
        url = block.get('url', 'N/A')
        relevance_score = block.get('relevance score', 'N/A')
        
        # Create clickable URL if it's a valid URL
        if url != 'N/A' and url.startswith('http'):
            url_display = f"[{url}]({url})"
        else:
            url_display = url
        
        block_text = f"""**Result #{result_number}**

**Title:** {title}

**Explanation:** {explanation}

**Matching Elements:** {matching_elements}

**URL:** {url_display}

**Relevance Score:** {relevance_score}

---"""
        formatted_blocks.append(block_text)
    
    return '\n\n'.join(formatted_blocks)

def format_fallback_response(response_text: str) -> str:
    """Fallback formatting for unstructured responses"""
    return f"**Response:**\n\n{response_text}"

def format_section_with_bold_titles(section_text: str) -> str:
    """Format a section to make field titles bold and inline"""
    if not section_text:
        return section_text
    
    lines = section_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for patterns like "Title: Some Title" or "Explanation: Some text"
        if ':' in line and len(line.split(':')) >= 2:
            parts = line.split(':', 1)
            title = parts[0].strip()
            content = parts[1].strip()
            
            if content:  # Only format if there's content after the colon
                formatted_line = f"**{title}:** {content}"
                formatted_lines.append(formatted_line)
            else:
                formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def parse_json_results(response_text: str) -> str:
    """Parse JSON results from Dify response and format them for display"""
    import json
    import re
    
    # Find JSON array in the response text
    json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
    if not json_match:
        return f"**Raw Response:**\n\n{response_text}"
    
    try:
        # Parse the JSON array
        json_str = json_match.group(0)
        results = json.loads(json_str)
        
        if not isinstance(results, list):
            return f"**Raw Response:**\n\n{response_text}"
        
        # Format each result
        formatted_blocks = []
        for i, result in enumerate(results, 1):
            title = result.get('title', 'N/A')
            explanation = result.get('explanation', 'N/A')
            matching_elements = result.get('matching_elements', 'N/A')
            url = result.get('url', 'N/A')
            relevance_score = result.get('relevance_score', 'N/A')
            
            # Create clickable URL if it's a valid URL
            if url != 'N/A' and url.startswith('http'):
                url_display = f"[{url}]({url})"
            else:
                url_display = url
            
            block_text = f"""**Result #{i}**

**Title:** {title}

**Explanation:** {explanation}

**Matching Elements:** {matching_elements}

**URL:** {url_display}

**Relevance Score:** {relevance_score}

---"""
            formatted_blocks.append(block_text)
        
        return '\n\n'.join(formatted_blocks)
        
    except json.JSONDecodeError:
        return f"**Raw Response:**\n\n{response_text}"

def check_backend_status():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_test_questions_from_db():
    """Retrieve test questions from the database via backend API"""
    try:
        response = requests.get(f"{BACKEND_URL}/test-questions", timeout=10)
        
        if response.status_code == 200:
            questions = response.json()
            return questions
        else:
            st.error(f"Backend error {response.status_code}: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error retrieving test questions: {e}")
        return []

def save_feedback_to_database(results, session_state):
    """Save feedback data to the results table"""
    try:
        import uuid
        from datetime import datetime
        
        # Generate a unique result ID for this submission
        result_id = str(uuid.uuid4())
        session_state.current_result_id = result_id
        
        # Get the current question text and ID
        question_text = session_state.get('question_input', '')
        question_id = session_state.get('selected_question_id')
        
        # If we have a question_id but no question_text, get the text from test questions
        if question_id is not None and not question_text:
            test_questions = get_test_questions_from_db()
            for q in test_questions:
                if q['question_id'] == question_id:
                    question_text = q['question_text']
                    break
        
        # Get SME user type
        sme_user_type = session_state.get('sme_user_type', 'Nurse')
        
        # Prepare data for each result
        results_data = []
        for i, result in enumerate(results, 1):
            result_key = f"result_{i}_feedback"
            feedback = session_state.get(result_key, {})
            
            # Convert is_relevant_sme from "Yes"/"No" to boolean
            is_relevant = None
            if feedback.get('is_relevant_sme') == "Yes":
                is_relevant = True
            elif feedback.get('is_relevant_sme') == "No":
                is_relevant = False
            
            result_entry = {
                'result_id': result_id,  # Same ID for all results in this submission
                'question_id': question_id,
                'question_text': question_text,
                'rank': i,  # AI-assigned position
                'title': result.get('title', ''),
                'explanation': result.get('explanation', ''),
                'tags_matched': result.get('matching_elements', ''),
                'url': result.get('url', ''),
                'relevance_score_model': float(result.get('relevance_score', 0)),
                'agent_version': '1.0',  # Default version
                'is_relevant_sme': is_relevant,
                'relevance_score_sme': feedback.get('relevance_score_sme', 0),
                'ideal_rank_sme': feedback.get('ideal_rank_sme', i),
                'sme_user_type': sme_user_type
            }
            results_data.append(result_entry)
        
        # Send to backend API
        response = requests.post(
            f"{BACKEND_URL}/save-results",
            json={'results': results_data},
            timeout=30
        )
        
        if response.status_code == 200:
            return True
        else:
            return False
            
    except Exception as e:
        return False

if __name__ == "__main__":
    # Check backend status on startup
    if not check_backend_status():
        st.error("""
        ⚠️ **Backend not available**
        
        Please make sure the backend server is running:
        1. Navigate to the `backend` folder
        2. Run: `python main.py`
        3. Ensure it's running on localhost:8001
        
        The frontend will still work, but searches will fail until the backend is available.
        """)
    
    main()
