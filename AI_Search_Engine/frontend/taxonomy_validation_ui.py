#!/usr/bin/env python3
"""
Taxonomy Validation UI
Streamlit interface for SMEs to label and validate content taxonomy
"""

import streamlit as st
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

try:
    from database import get_connection
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Taxonomy Validation",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .content-box {
        background-color: white;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .summary-box {
        max-height: 300px;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fafafa;
    }
    .tags-display {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .tag-item {
        background-color: #e3f2fd;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
    }
    .stats-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    .content-label {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2c3e50;
    }
    .stats-number {
        font-size: 1.1rem;
        font-weight: bold;
        color: #495057;
    }
    .main-title {
        margin-top: 0;
        padding-top: 0;
    }
    /* Reduce top whitespace */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    /* Hide Streamlit header */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Alternative: if you want to keep header but reduce it */
    /* header {
        padding-top: 0.5rem !important;
        height: 2rem !important;
    } */
    /* Reduce main title spacing */
    h1, h2, h3 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    /* Reduce spacing between rows */
    .element-container {
        margin-bottom: 0.5rem !important;
    }
    /* Reduce spacing between columns */
    .row-widget.stHorizontal {
        margin-bottom: 0.5rem !important;
    }
    /* Reduce spacing for specific content rows */
    div[data-testid="column"] {
        margin-bottom: 0.25rem !important;
    }
    /* Reduce spacing around horizontal rules (divider lines) */
    hr {
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
        border: none !important;
        border-top: 1px solid #e0e0e0 !important;
    }
    /* Reduce spacing around markdown elements */
    .stMarkdown {
        margin-bottom: 0.5rem !important;
    }
    
    /* Style auto tag plus buttons to be small and integrated */
    .stButton > button[key*="add_auto_tag_"] {
        width: 20px !important;
        height: 20px !important;
        min-width: 20px !important;
        padding: 0 !important;
        margin: 0 !important;
        border-radius: 50% !important;
        font-size: 10px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #f8f9fa !important;
        border: 1px solid #dee2e6 !important;
        color: #6c757d !important;
        position: relative !important;
        left: auto !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    
    .stButton > button[key*="add_auto_tag_"]:hover {
        background-color: #e9ecef !important;
        border-color: #adb5bd !important;
    }
    
    /* Style for taxonomy dropdown */
    .stSelectbox > div > div > div > div {
        font-family: 'Courier New', monospace;
        line-height: 1.4;
    }
    
    /* Add some spacing for better readability */
    .stSelectbox {
        margin-bottom: 1rem;
    }
    
    /* Make the taxonomy label more prominent */
    .stSelectbox label {
        font-weight: bold;
        color: #2c3e50;
    }
    
    /* Style for the dropdown options */
    .stSelectbox select option {
        padding: 4px 8px;
        font-size: 14px;
    }
    
    /* Add visual separation between categories */
    .stSelectbox select option[value*="📁"] {
        font-weight: bold;
        color: #6c757d;
        background-color: #f8f9fa;
    }
    
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_database_stats():
    """Get database statistics for the header"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Total content
            cursor.execute("SELECT COUNT(*) FROM content_master")
            total_content = cursor.fetchone()[0]
            
            # Fast Facts content
            cursor.execute("SELECT COUNT(*) FROM content_master WHERE source = 'Fast Fact'")
            fast_facts_count = cursor.fetchone()[0]
            
            # UD content
            cursor.execute("SELECT COUNT(*) FROM content_master WHERE source = 'UD'")
            ud_content_count = cursor.fetchone()[0]
            
            # Unlabeled content
            cursor.execute("SELECT COUNT(*) FROM content_master WHERE labels_approved = FALSE")
            unlabeled_count = cursor.fetchone()[0]
            
            return {
                'total': total_content,
                'fast_facts': fast_facts_count,
                'ud_content': ud_content_count,
                'unlabeled': unlabeled_count
            }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return None

@st.cache_data(ttl=300)
def get_taxonomy_categories():
    """Get unique categories from the taxonomy_master table"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get unique categories from taxonomy_master
            cursor.execute("""
                SELECT DISTINCT category 
                FROM taxonomy_master 
                WHERE category IS NOT NULL AND category != '' 
                ORDER BY category
            """)
            categories = [row[0] for row in cursor.fetchall()]
            
            return categories
    except Exception as e:
        logger.error(f"Error getting taxonomy categories: {e}")
        return []

@st.cache_data(ttl=300)
def get_taxonomy_subcategories(category: str = None):
    """Get subcategories from taxonomy_master table, optionally filtered by category"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            if category:
                # Get subcategories for specific category
                cursor.execute("""
                    SELECT DISTINCT sub_category 
                    FROM taxonomy_master 
                    WHERE category = ? AND sub_category IS NOT NULL AND sub_category != ''
                    ORDER BY sub_category
                """, (category,))
            else:
                # Get all unique subcategories
                cursor.execute("""
                    SELECT DISTINCT sub_category 
                    FROM taxonomy_master 
                    WHERE sub_category IS NOT NULL AND sub_category != '' 
                    ORDER BY sub_category
                """)
            
            subcategories = [row[0] for row in cursor.fetchall()]
            
            # Check if the category has any subcategories
            if category:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM taxonomy_master 
                    WHERE category = ? AND sub_category IS NOT NULL AND sub_category != ''
                """, (category,))
                has_subcategories = cursor.fetchone()[0] > 0
                return subcategories, has_subcategories
            
            return subcategories, True
    except Exception as e:
        logger.error(f"Error getting taxonomy subcategories: {e}")
        return [], True

def build_taxonomy_options():
    """
    Build hierarchical taxonomy options for the unified dropdown.
    Returns a list of options with L1/L2 prefixes and indentation.
    Only includes selectable options (L1 without subcategories and L2 subcategories).
    """
    categories = get_taxonomy_categories()
    options = []
    
    for category in categories:
        subcategories, has_subcategories = get_taxonomy_subcategories(category)
        
        if has_subcategories:
            # Add category as a header (non-selectable)
            options.append(f"📁 {category}")
            # Add subcategories as selectable options
            for subcategory in subcategories:
                options.append(f"    └─ {subcategory}")
        else:
            # Category has no subcategories - add as selectable option
            options.append(f"📄 {category}")
    
    return options

def parse_taxonomy_selection(selected_option):
    """
    Parse the selected taxonomy option and return category and subcategory.
    Returns (category, subcategory) where subcategory can be None.
    """
    if not selected_option or selected_option == "Select taxonomy...":
        return None, None
    
    if selected_option.startswith("📄 "):
        # L1 selection (no subcategories)
        category = selected_option[2:]  # Remove "📄 " prefix
        return category, None
    elif selected_option.startswith("    └─ "):
        # L2 selection - indented subcategory
        subcategory = selected_option[7:]  # Remove "    └─ " prefix
        
        # Find the parent category by looking at the hierarchy
        categories = get_taxonomy_categories()
        for category in categories:
            subcategories, has_subcategories = get_taxonomy_subcategories(category)
            if has_subcategories and subcategory in subcategories:
                return category, subcategory
        
        # Fallback if not found
        return None, subcategory
    
    return None, None

@st.cache_data(ttl=300)
def get_categories_and_subcategories():
    """Get existing categories and subcategories from the database (legacy function for backward compatibility)"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get unique categories (excluding empty/null)
            cursor.execute("""
                SELECT DISTINCT category 
                FROM content_master 
                WHERE category IS NOT NULL AND category != '' 
                ORDER BY category
            """)
            categories = [row[0] for row in cursor.fetchall()]
            
            # Get unique subcategories (excluding empty/null)
            cursor.execute("""
                SELECT DISTINCT sub_category 
                FROM content_master 
                WHERE sub_category IS NOT NULL AND sub_category != '' 
                ORDER BY sub_category
            """)
            subcategories = [row[0] for row in cursor.fetchall()]
            
            return categories, subcategories
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return [], []

@st.cache_data(ttl=300)
def get_existing_tags():
    """Get existing tags from the database"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get tags from only the tags column (not FF_tags)
            cursor.execute("""
                SELECT tags FROM content_master 
                WHERE tags IS NOT NULL AND tags != ''
            """)
            tags_rows = cursor.fetchall()
            
            all_tags = set()
            
            # Parse tags from JSON strings
            for row in tags_rows:
                try:
                    if row[0]:
                        tags = json.loads(row[0])
                        if isinstance(tags, list):
                            all_tags.update(tags)
                except:
                    continue
            
            return sorted(list(all_tags))
    except Exception as e:
        logger.error(f"Error getting existing tags: {e}")
        return []

def get_unlabeled_content(content_type: str) -> List[Dict[str, Any]]:
    """Get unlabeled content filtered by type"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, source, summary, FF_tags, category, sub_category, tags, url
                FROM content_master 
                WHERE labels_approved = FALSE AND source = ?
                ORDER BY id
            """, (content_type,))
            
            rows = cursor.fetchall()
            content_list = []
            
            for row in rows:
                content_dict = dict(row)
                
                # Parse FF_tags
                if content_dict.get('FF_tags'):
                    try:
                        content_dict['FF_tags'] = json.loads(content_dict['FF_tags'])
                    except:
                        content_dict['FF_tags'] = []
                else:
                    content_dict['FF_tags'] = []
                
                # Parse tags
                if content_dict.get('tags'):
                    try:
                        content_dict['tags'] = json.loads(content_dict['tags'])
                    except:
                        content_dict['tags'] = []
                else:
                    content_dict['tags'] = []
                
                content_list.append(content_dict)
            
            return content_list
    except Exception as e:
        logger.error(f"Error getting unlabeled content: {e}")
        return []

def get_content_by_id(content_id: str) -> Optional[Dict[str, Any]]:
    """Get specific content by ID"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, source, summary, FF_tags, auto_tags, category, sub_category, tags, url
                FROM content_master 
                WHERE id = ?
            """, (content_id,))
            
            row = cursor.fetchone()
            if row:
                content_dict = dict(row)
                
                # Parse FF_tags
                if content_dict.get('FF_tags'):
                    try:
                        content_dict['FF_tags'] = json.loads(content_dict['FF_tags'])
                    except:
                        content_dict['FF_tags'] = []
                else:
                    content_dict['FF_tags'] = []
                
                # Parse tags
                if content_dict.get('tags'):
                    try:
                        content_dict['tags'] = json.loads(content_dict['tags'])
                    except:
                        content_dict['tags'] = []
                else:
                    content_dict['tags'] = []
                
                # Parse auto_tags
                if content_dict.get('auto_tags'):
                    try:
                        content_dict['auto_tags'] = json.loads(content_dict['auto_tags'])
                    except:
                        content_dict['auto_tags'] = []
                else:
                    content_dict['auto_tags'] = []
                
                return content_dict
            return None
    except Exception as e:
        logger.error(f"Error getting content by ID: {e}")
        return None

def save_labels(content_id: str, category: str, sub_category: str, tags: List[str]) -> bool:
    """Save labels to the database"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert tags list to JSON string
            tags_json = json.dumps(tags) if tags else None
            
            cursor.execute("""
                UPDATE content_master 
                SET category = ?, sub_category = ?, tags = ?, labels_approved = TRUE, last_edited = ?
                WHERE id = ?
            """, (category, sub_category, tags_json, datetime.now().date(), content_id))
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving labels: {e}")
        return False

def main():
    """Main application function"""
    
    # Header - Removed as requested
    
    # Initialize session state
    if 'selected_content_type' not in st.session_state:
        st.session_state.selected_content_type = "Fast Fact"
    if 'selected_content_id' not in st.session_state:
        st.session_state.selected_content_id = None
    if 'show_new_tag_input' not in st.session_state:
        st.session_state.show_new_tag_input = False
    if 'new_tags_added' not in st.session_state:
        st.session_state.new_tags_added = []
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = "Select category..."
    if 'previous_content_id' not in st.session_state:
        st.session_state.previous_content_id = None
    
    # 🟩 1. Header / Overview Section
    # Header removed as requested
    
    stats = get_database_stats()
    if stats:
        # Get unlabeled counts
        ud_unlabeled = len(get_unlabeled_content("UD"))
        ff_unlabeled = len(get_unlabeled_content("Fast Fact"))
        
        # Create a single container with both rows using HTML
        stats_html = f"""
        <div style="margin-bottom: 0.5rem;">
            <div style="display: flex; margin-bottom: 0.25rem;">
                <div style="flex: 1.2; padding-left: 120px; display: flex; align-items: center;">
                    <span class="content-label">UD Content</span>
                </div>
                <div style="flex: 1;">
                    <span class="stats-number">Total Content Count: </span><span style="font-size: 1.7rem; font-weight: bold; color: #e74c3c;">{stats["ud_content"]}</span>
                </div>
                <div style="flex: 1;">
                    <span class="stats-number">Needs Labeling Count: </span><span style="font-size: 1.7rem; font-weight: bold; color: #e74c3c;">{ud_unlabeled}</span>
                </div>
            </div>
            <div style="display: flex;">
                <div style="flex: 1.2; padding-left: 120px; display: flex; align-items: center;">
                    <span class="content-label">Fast Fact Content</span>
                </div>
                <div style="flex: 1;">
                    <span class="stats-number">Total Content Count: </span><span style="font-size: 1.7rem; font-weight: bold; color: #e74c3c;">{stats["fast_facts"]}</span>
                </div>
                <div style="flex: 1;">
                    <span class="stats-number">Needs Labeling Count: </span><span style="font-size: 1.7rem; font-weight: bold; color: #e74c3c;">{ff_unlabeled}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(stats_html, unsafe_allow_html=True)
    else:
        st.error("❌ Unable to load database statistics. Please check your database connection.")
        return
    
    st.markdown("---")
    
    # 🟦 2. Labeling Configuration Bar
    # Content type selection
    content_type = st.radio(
        "Select Content Source to label",
        ["Fast Fact", "UD"],
        index=0
    )
    
    # Update session state
    st.session_state.selected_content_type = content_type
    
    # Get unlabeled content for selected type
    unlabeled_content = get_unlabeled_content(content_type)
    
    # 🟨 3. Content Selection
    # Create selection options
    if unlabeled_content:
        content_options = [f"{item['id']} - {item['title'][:100]}" for item in unlabeled_content]
        content_ids = [item['id'] for item in unlabeled_content]
        
        # Content selection dropdown
        selected_option = st.selectbox(
            f"Choose content to label",
            ["Select content..."] + content_options,
            index=0
        )
        
        if selected_option == "Select content...":
            st.info("Please select content from the dropdown above to begin labeling.")
            return
        
        # Get selected content ID
        selected_content_id = content_ids[content_options.index(selected_option)]
        st.session_state.selected_content_id = selected_content_id
        
        # Reset form if content has changed
        if st.session_state.previous_content_id != selected_content_id:
            st.session_state.selected_category = "Select category..."
            st.session_state.new_tags_added = []
            st.session_state.selected_tags_from_auto = []
            st.session_state.show_new_tag_input = False
            st.session_state.previous_content_id = selected_content_id
    else:
        st.info(f"There is no content for this source that needs labels.")
        return
    
    # Get full content details
    selected_content = get_content_by_id(selected_content_id)
    
    if not selected_content:
        st.error("❌ Unable to load selected content. Please try again.")
        return
    
    # Small divider with minimal spacing
    st.markdown('<hr style="margin: 0.25rem 0;">', unsafe_allow_html=True)
    
    # 🟧 4. Labeling Form Panel - Split Layout
    st.markdown("### 🏷️ Content Labeling")
    
    # Get categories and tags for form (needed in both columns)
    categories = get_taxonomy_categories()
    existing_tags = get_existing_tags()
    
    # Create two columns: 2/3 for content, 1/3 for labels
    content_col, labels_col = st.columns([2, 1])
    
    with content_col:
        # Display content details
        st.markdown(f"**Title:** {selected_content['title']}")
        
        # Summary in scrollable box
        st.markdown("**Summary:**")
        st.markdown(f"""
        <div class="summary-box">
            {selected_content['summary']}
        </div>
        """, unsafe_allow_html=True)
        
        # URL link
        if selected_content.get('url'):
            st.markdown(f"**URL:** [{selected_content['url']}]({selected_content['url']})")
        
        # FF_tags display
        if selected_content['FF_tags']:
            st.markdown("**FastFact Tags:**")
            tags_html = '<div class="tags-display">'
            for tag in selected_content['FF_tags']:
                tags_html += f'<span class="tag-item">{tag}</span>'
            tags_html += '</div>'
            st.markdown(tags_html, unsafe_allow_html=True)
        
        # Auto Tags display
        if selected_content['auto_tags']:
            st.markdown("**Auto Tags:**")
            
            # Get selected auto tags to filter out already selected ones
            selected_auto_tags = st.session_state.get('selected_tags_from_auto', [])
            
            # Filter out tags that are already selected
            available_auto_tags = [tag for tag in selected_content['auto_tags'] if tag not in selected_auto_tags]
            
            if available_auto_tags:
                # Create auto tags with small plus buttons
                for i, tag in enumerate(available_auto_tags):
                    col1, col2 = st.columns([0.3, 4.7])
                    with col1:
                        if st.button("➕", key=f"add_auto_tag_{selected_content_id}_{i}", help=f"Add '{tag}' to selected tags"):
                            # Check if tag exists in existing tags list
                            if tag in existing_tags:
                                # Tag exists in existing tags, add it to the multiselect default
                                if 'selected_tags_from_auto' not in st.session_state:
                                    st.session_state.selected_tags_from_auto = []
                                if tag not in st.session_state.selected_tags_from_auto:
                                    st.session_state.selected_tags_from_auto.append(tag)
                                st.rerun()
                            else:
                                # Tag doesn't exist in existing tags, add to bottom section as before
                                if tag not in st.session_state.get('selected_tags_from_auto', []):
                                    if 'selected_tags_from_auto' not in st.session_state:
                                        st.session_state.selected_tags_from_auto = []
                                    st.session_state.selected_tags_from_auto.append(tag)
                                    st.rerun()
                    with col2:
                        st.markdown(f'<span class="tag-item" style="background-color: #e8f5e8; color: #2e7d32; display: inline-block; vertical-align: middle; margin-top: 4px;">{tag}</span>', unsafe_allow_html=True)
            else:
                st.markdown("*All auto tags have been selected*")
        else:
            st.markdown("**Auto Tags:**")
            st.markdown("*No automatic tags exist*")
    
    with labels_col:
        # Check if taxonomy data exists
        if not categories:
            st.error("❌ No taxonomy categories found. Please run the taxonomy ingestion pipeline first.")
            return
        
        # Labeling form
        st.markdown("**Apply Labels:**")
        
        # Unified taxonomy selection
        all_taxonomy_options = ["Select taxonomy..."] + build_taxonomy_options()
        
        # Filter out category headers (📁) to make them non-selectable
        selectable_options = ["Select taxonomy..."]
        for option in all_taxonomy_options[1:]:  # Skip "Select taxonomy..."
            if not option.startswith("📁 "):  # Only include selectable options
                selectable_options.append(option)
        
        # Get current selection for default value
        current_selection = "Select taxonomy..."
        if st.session_state.get('selected_taxonomy'):
            current_selection = st.session_state.selected_taxonomy
        
        # Find the index of current selection
        current_index = 0
        if current_selection in selectable_options:
            current_index = selectable_options.index(current_selection)
        
        selected_taxonomy = st.selectbox(
            "Select Taxonomy *",
            selectable_options,
            index=current_index,
            key=f"taxonomy_select_{selected_content_id}"
        )
        
        # Update session state when taxonomy changes
        if selected_taxonomy != st.session_state.get('selected_taxonomy'):
            st.session_state.selected_taxonomy = selected_taxonomy
            st.rerun()
        
        # Parse the selection to get category and subcategory
        category, subcategory = parse_taxonomy_selection(selected_taxonomy)
        
        # Tags selection with ability to add new ones
        st.markdown("**Tags *:**")
        
        # Full-width existing tags selection
        # Get auto tags that exist in the existing tags list
        auto_tags_in_existing = []
        if st.session_state.get('selected_tags_from_auto', []):
            auto_tags_in_existing = [tag for tag in st.session_state.selected_tags_from_auto if tag in existing_tags]
        
        # Track previous selection to detect removals
        previous_selection_key = f"previous_selection_{selected_content_id}"
        if previous_selection_key not in st.session_state:
            st.session_state[previous_selection_key] = auto_tags_in_existing
        
        selected_tags = st.multiselect(
            "Select existing tags",
            existing_tags,
            default=auto_tags_in_existing,
            key=f"tags_select_{selected_content_id}"
        )
        
        # Check for removed auto tags and add them back to available list
        previous_selection = st.session_state[previous_selection_key]
        removed_tags = [tag for tag in previous_selection if tag not in selected_tags]
        
        # Only handle auto tags that were removed
        removed_auto_tags = [tag for tag in removed_tags if tag in st.session_state.get('selected_tags_from_auto', [])]
        
        if removed_auto_tags:
            # Remove these tags from the session state so they reappear on the left
            for tag in removed_auto_tags:
                if tag in st.session_state.selected_tags_from_auto:
                    st.session_state.selected_tags_from_auto.remove(tag)
            st.rerun()
        
        # Update previous selection for next iteration
        st.session_state[previous_selection_key] = selected_tags
        
        # Create new tag button and input
        if st.button("➕ Create New Tag", key=f"create_tag_btn_{selected_content_id}"):
            st.session_state.show_new_tag_input = True
        
        # Show new tag input if button was clicked
        new_tag = ""
        if st.session_state.get('show_new_tag_input', False):
            # Use a different key that we can reset
            input_key = f"new_tag_input_{selected_content_id}_{len(st.session_state.get('new_tags_added', []))}"
            new_tag = st.text_input("Enter new tag name:", key=input_key)
            if new_tag and new_tag.strip():
                new_tag_clean = new_tag.strip()
                
                # Check if tag already exists in existing tags list (case-insensitive)
                existing_tag_found = None
                for existing_tag in existing_tags:
                    if new_tag_clean.lower() == existing_tag.lower():
                        existing_tag_found = existing_tag
                        break
                
                if existing_tag_found:
                    # Tag exists (case-insensitive match) - add it to the existing tags selection instead of new tags
                    if existing_tag_found not in selected_tags:
                        # Add to session state to update the multiselect default
                        if 'selected_tags_from_auto' not in st.session_state:
                            st.session_state.selected_tags_from_auto = []
                        if existing_tag_found not in st.session_state.selected_tags_from_auto:
                            st.session_state.selected_tags_from_auto.append(existing_tag_found)
                    st.success(f"✅ Tag '{new_tag_clean}' matches existing tag '{existing_tag_found}' and has been selected!")
                    st.rerun()
                else:
                    # Tag doesn't exist - add to new tags list for this session
                    if new_tag_clean not in st.session_state.new_tags_added:
                        st.session_state.new_tags_added.append(new_tag_clean)
                        st.rerun()
        
        # Display auto tags that have been selected (only those not in existing tags list)
        auto_tags_not_in_existing = []
        if st.session_state.get('selected_tags_from_auto', []):
            auto_tags_not_in_existing = [tag for tag in st.session_state.selected_tags_from_auto if tag not in existing_tags]
        
        if auto_tags_not_in_existing:
            st.markdown("**Auto Tags Selected:**")
            
            # Display each auto tag on its own row with individual remove button on the left
            for i, tag in enumerate(auto_tags_not_in_existing):
                col1, col2 = st.columns([0.3, 4.7])
                with col1:
                    if st.button("×", key=f"remove_auto_tag_{selected_content_id}_{i}", help="Remove this auto tag"):
                        # Remove from session state
                        if tag in st.session_state.selected_tags_from_auto:
                            st.session_state.selected_tags_from_auto.remove(tag)
                        st.rerun()
                with col2:
                    st.markdown(f'<span class="tag-item" style="background-color: #e8f5e8; color: #2e7d32; display: inline-block; vertical-align: middle; margin-top: 4px;">{tag}</span>', unsafe_allow_html=True)
            

        
        # Display newly added tags
        if st.session_state.get('new_tags_added', []):
            st.markdown("**Newly Added Tags:**")
            
            # Display each tag on its own row with individual remove button on the left
            for i, tag in enumerate(st.session_state.new_tags_added):
                col1, col2 = st.columns([0.3, 4.7])
                with col1:
                    if st.button("×", key=f"remove_tag_{selected_content_id}_{i}", help="Remove this tag"):
                        st.session_state.new_tags_added.pop(i)
                        st.rerun()
                with col2:
                    st.markdown(f'<span class="tag-item" style="background-color: #ffebee; color: #c62828; display: inline-block; vertical-align: middle; margin-top: 4px;">{tag}</span>', unsafe_allow_html=True)
            
            # Option to remove all new tags
            if st.button("Remove All New Tags", key=f"remove_all_new_tags_{selected_content_id}"):
                st.session_state.new_tags_added = []
                st.rerun()
    
    # Combine existing, new, and auto tags
    all_tags = selected_tags.copy()
    all_tags.extend(st.session_state.get('new_tags_added', []))
    # Only add auto tags that are not already in the existing tags list (to avoid duplicates)
    auto_tags_not_in_existing = []
    if st.session_state.get('selected_tags_from_auto', []):
        auto_tags_not_in_existing = [tag for tag in st.session_state.selected_tags_from_auto if tag not in existing_tags]
    all_tags.extend(auto_tags_not_in_existing)
    
    # Show tag count indicator
    tag_count = len(all_tags)
    if tag_count == 0:
        st.markdown(f"<span style='color: #e74c3c; font-size: 0.9em;'>⚠️ No tags selected (at least 1 required)</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span style='color: #27ae60; font-size: 0.9em;'>✅ {tag_count} tag(s) selected</span>", unsafe_allow_html=True)
    
    # Submit button centered at the bottom
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        submit_button = st.button("✅ Submit Labels", type="primary", use_container_width=True, key=f"submit_btn_{selected_content_id}")
    
    if submit_button:
        # Validation
        if selected_taxonomy == "Select taxonomy...":
            st.error("❌ Please select a taxonomy before submitting.")
        elif not all_tags:  # Check if no tags are selected or created
            st.error("❌ Please select at least one tag before submitting.")
        else:
            # Parse the taxonomy selection
            category, subcategory = parse_taxonomy_selection(selected_taxonomy)
            
            # Save labels
            success = save_labels(selected_content_id, category, subcategory, all_tags)
            
            if success:
                st.success("✅ Labels saved successfully!")
                
                # Clear cache to refresh data
                get_database_stats.clear()
                
                # Reset all form selections
                st.session_state.selected_content_id = None
                st.session_state.selected_taxonomy = "Select taxonomy..."
                st.session_state.selected_tags_from_auto = []
                st.session_state.new_tags_added = []
                st.session_state.show_new_tag_input = False
                
                # Rerun to refresh the interface
                st.rerun()
            else:
                st.error("❌ Failed to save labels. Please try again.")

if __name__ == "__main__":
    main()
