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
            
            # Get tags from both tags and FF_tags columns
            cursor.execute("""
                SELECT tags FROM content_master 
                WHERE tags IS NOT NULL AND tags != ''
            """)
            tags_rows = cursor.fetchall()
            
            cursor.execute("""
                SELECT FF_tags FROM content_master 
                WHERE FF_tags IS NOT NULL AND FF_tags != ''
            """)
            ff_tags_rows = cursor.fetchall()
            
            all_tags = set()
            
            # Parse tags from JSON strings
            for row in tags_rows + ff_tags_rows:
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
                SELECT id, title, source, summary, FF_tags, category, sub_category, tags, url
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
    
    with labels_col:
        # Get categories and tags for form
        categories = get_taxonomy_categories()
        existing_tags = get_existing_tags()
        
        # Check if taxonomy data exists
        if not categories:
            st.error("❌ No taxonomy categories found. Please run the taxonomy ingestion pipeline first.")
            return
        
        # Labeling form
        st.markdown("**Apply Labels:**")
        
        # Category selection
        category_options = ["Select category..."] + categories
        current_index = 0
        if st.session_state.selected_category != "Select category...":
            try:
                current_index = category_options.index(st.session_state.selected_category)
            except ValueError:
                current_index = 0
        
        category = st.selectbox(
            "Category *",
            category_options,
            index=current_index,
            key=f"category_select_{selected_content_id}"
        )
        
        # Update session state when category changes
        if category != st.session_state.selected_category:
            st.session_state.selected_category = category
            # Clear subcategory cache to get fresh data
            get_taxonomy_subcategories.clear()
            st.rerun()
        
        # Dynamic subcategory selection based on selected category
        if category != "Select category...":
            subcategories, has_subcategories = get_taxonomy_subcategories(category)
            
            if has_subcategories:
                # Category has subcategories, show them
                subcategory = st.selectbox(
                    "Sub-category *",
                    ["Select sub-category..."] + subcategories,
                    index=0,
                    key=f"subcategory_select_{selected_content_id}"
                )
            else:
                # Category has no subcategories, auto-populate with "No Sub Category Needed"
                st.selectbox(
                    "Sub-category *",
                    ["No Sub Category Needed"],
                    index=0,
                    key=f"subcategory_select_{selected_content_id}"
                )
                subcategory = "No Sub Category Needed"
        else:
            # No category selected, show empty subcategory dropdown
            subcategory = st.selectbox(
                "Sub-category *",
                ["Select sub-category..."],
                index=0,
                key=f"subcategory_select_{selected_content_id}"
            )
        
        # Tags selection with ability to add new ones
        st.markdown("**Tags *:**")
        
        # Full-width existing tags selection
        selected_tags = st.multiselect(
            "Select existing tags",
            existing_tags,
            default=[],
            key=f"tags_select_{selected_content_id}"
        )
        
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
                # Add to new tags list for this session
                if new_tag_clean not in st.session_state.new_tags_added:
                    st.session_state.new_tags_added.append(new_tag_clean)
                    st.rerun()
        
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
    
    # Combine existing and new tags
    all_tags = selected_tags.copy()
    all_tags.extend(st.session_state.get('new_tags_added', []))
    
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
        if category == "Select category...":
            st.error("❌ Please select a category before submitting.")
        elif subcategory == "Select sub-category...":
            st.error("❌ Please select a sub-category before submitting.")
        elif not all_tags:  # Check if no tags are selected or created
            st.error("❌ Please select at least one tag before submitting.")
        else:
            # Handle "No Sub Category Needed" case
            if subcategory == "No Sub Category Needed":
                subcategory_to_save = None
            else:
                subcategory_to_save = subcategory
            
            # Save labels
            success = save_labels(selected_content_id, category, subcategory_to_save, all_tags)
            
            if success:
                st.success("✅ Labels saved successfully!")
                
                # Clear cache to refresh data
                get_database_stats.clear()
                
                # Reset selection
                st.session_state.selected_content_id = None
                
                # Rerun to refresh the interface
                st.rerun()
            else:
                st.error("❌ Failed to save labels. Please try again.")

if __name__ == "__main__":
    main()
