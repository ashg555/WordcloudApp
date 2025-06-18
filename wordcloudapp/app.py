import streamlit as st
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from gemini_helper import generate_traits, ask_question
from matplotlib.colors import to_hex
from matplotlib.cm import plasma

char_name = ""
st.session_state.show_editors = True

current_script_dir = os.path.dirname(__file__)
font_file_path = os.path.join(current_script_dir, "fonts", "SourceSansPro-Regular.ttf")

# Initialize session state
if "current_character" not in st.session_state:
    st.session_state.current_character = None
    
if "last_update" not in st.session_state:
    st.session_state.last_update = {}

if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

if "conversation" not in st.session_state:
    st.session_state.conversation = []

if "custom_question" not in st.session_state:
    st.session_state.custom_question = ""

# Character management functions
def load_character(name):
    with open(f"characters/{name}.json") as f:
        return json.load(f)

def save_character(data):
    char_name = data["character"]
    with open(f"characters/{char_name}.json", "w") as f:
        json.dump(data, f, indent=2)

def create_character(name):
    new_char = {
        "character": name,
        "history": [
            {
                "version": 1,
                "timestamp": datetime.now().isoformat(),
                "traits": {}
            }
        ]
    }
    save_character(new_char)
    return new_char

# JSON Helper Functions
def traits_to_text(traits):
    """Convert traits dict to sorted, formatted text with visual hierarchy"""
    if not traits:
        return "(No traits yet)"
    # Sort by absolute value descending, then alphabetically
    sorted_traits = sorted(
        traits.items(),
        key=lambda x: (-abs(x[1]), x[0].lower())
    )
    # Format with visual indicators
    lines = []
    for trait, weight in sorted_traits:
        line = f"{trait}: {weight}"
        lines.append(line)
    
    return "\n".join(lines)

def text_to_traits(text):
    """Parse text area content back to traits dict"""
    traits = {}
    for line in text.split("\n"):
        line = line.strip()
        if ":" in line:
            trait, weight_str = line.split(":", 1)
            trait = trait.strip()
            try:
                weight = int(weight_str.strip())
                traits[trait] = weight
            except ValueError:
                continue  # Skip invalid lines
    return traits

def get_quadrant_color(value, min_val, max_val):
    """Assign color based on value's position in the range"""
    # Normalize value to 0-1 range
    normalized = (value - min_val) / (max_val - min_val) if max_val != min_val else 0.5
    
    # Define quadrant ranges
    if normalized < 0.25:
        return to_hex(plasma(0.1))  # Dark purple (bottom 25%)
    elif normalized < 0.5:
        return to_hex(plasma(0.35))  # Purple-blue (mid-bottom 25%)
    elif normalized < 0.75:
        return to_hex(plasma(0.6))   # Orange-red (mid-top 25%)
    else:
        return to_hex(plasma(0.95))  # Bright yellow (top 25%)

# UI Components
def trait_editor(traits):
    st.subheader("Edit Traits")
    new_traits = traits.copy()
    
    # Track traits to remove
    to_remove = set()
    
    for trait in traits:
        cols = st.columns([2, 6, 2])
        cols[0].write(trait)
        
        # Allow negative adjustments
        new_value = cols[1].slider(
            "Weight", 0, 50, traits[trait], 
            key=f"weight_{trait}"
        )
        
        # Mark for removal if ≤0
        if new_value <= 0:
            to_remove.add(trait)
        else:
            new_traits[trait] = new_value
            
        # Manual removal button
        if cols[2].button("X", key=f"del_{trait}"):
            to_remove.add(trait)
    
    # Remove marked traits
    for trait in to_remove:
        if trait in new_traits:
            del new_traits[trait]
    
    # Add new trait (with validation)
    with st.expander("+ Add Custom Trait"):
        new_name = st.text_input("Trait Name")
        new_weight = st.slider("Initial Weight", 0, 50, 1)
        
        if st.button("Add") and new_name:
            # Only add if positive weight
            if new_weight > 0:
                new_traits[new_name] = new_weight
            else:
                st.warning("Traits must start with positive weight")
    
    return new_traits

# def normalize_weights(traits, max_weight=50):
#     """Scale weights proportionally to a max value"""
#     if not traits: return traits
    
#     max_val = max(traits.values())
#     if max_val <= max_weight: 
#         return traits
        
#     return {k: int(v * max_weight / max_val) 
#             for k, v in traits.items()}

def render_wordcloud(traits):
    if not traits:
        st.text("No traits to display yet.")
        return
    
    if not os.path.exists(font_file_path):
        st.error(f"Error: Font file not found at: {font_file_path}")
        return
    
    wc = WordCloud(
        width=800, 
        height=400, 
        font_path=font_file_path,
        background_color="white", 
        colormap="plasma")
    
    # normalized_traits = normalize_weights(traits)
    wc.generate_from_frequencies(traits)
    
    fig, ax = plt.subplots()
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    st.pyplot(fig)

# Main App Flow
def main():
    st.markdown("""
    <style>
    div[data-baseweb="textarea"] {
        border: 1px solid #4a8cff !important;
        border-radius: 8px !important;
    }
    textarea {
        font-family: monospace !important;
        line-height: 1.5 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("Character Wordcloud Profiler")
    
    # Sidebar - Character Selection
    st.sidebar.header("Character Manager")
    characters = [f[:-5] for f in os.listdir("characters") if f.endswith(".json")]
    
    new_char = st.sidebar.text_input("Create New Character")
    if st.sidebar.button("Create") and new_char:
        create_character(new_char)
        characters.append(new_char)
    
    selected_char = st.sidebar.selectbox("Select Character", characters)
    
    # Reset last_update when character changes
    if "prev_selected_char" not in st.session_state:
        st.session_state.prev_selected_char = selected_char
    elif st.session_state.prev_selected_char != selected_char: # Clear fields on character change
        st.session_state.last_update = {}
        st.session_state["description"] = ""
        st.session_state.last_analysis = None
        st.session_state.conversation = []
        st.session_state.custom_question = ""
        st.session_state.prev_selected_char = selected_char

    if selected_char:
        char_data = load_character(selected_char)
        current_version = char_data["history"][-1]
        
        # Trait Generation Panel
        st.subheader("Trait Generator")
        description = st.text_area("Character Description", height=150, key="description")
        if st.button("Generate Traits"):
            previous_traits = char_data["history"][-1]["traits"].copy()
            generated_traits = generate_traits(description, char_name, current_version["traits"])
            
            # Save deltas for display
            deltas = {}
            for trait, weight in generated_traits.items():
                old_value = previous_traits.get(trait, 0)
                new_value = old_value + weight
                deltas[trait] = weight 
            st.session_state.last_update = deltas

            # Start with previous traits
            combined_traits = previous_traits.copy()

            # Update/add generated traits
            for trait, weight in generated_traits.items():
                combined_traits[trait] = combined_traits.get(trait, 0) + weight

            # Remove traits with non-positive weights
            combined_traits = {k: v for k, v in combined_traits.items() if v > 0}

            current_version = {
                "version": len(char_data["history"]) + 1,
                "timestamp": datetime.now().isoformat(),
                "traits": combined_traits
            }

            char_data["history"].append(current_version)

            save_character(char_data)
            
            st.session_state.show_editors = True  # Show editors after generation

        # Display last update
        if st.session_state.last_update:
            st.subheader("Recent Updates")
            
            # Create columns for positive/negative changes
            pos_col, neg_col = st.columns(2)
            
            with pos_col:
                st.markdown("**Strengthened Traits**")
                for trait, delta in st.session_state.last_update.items():
                    if delta > 0:
                        st.success(f"{trait} +{delta}")
            
            with neg_col:
                st.markdown("**Weakened Traits**")
                for trait, delta in st.session_state.last_update.items():
                    if delta < 0:
                        st.error(f"{trait} {delta}")
            
            # Show removed traits separately
            removed = [
                trait for trait, delta in st.session_state.last_update.items()
                if char_data["history"][-1]["traits"].get(trait, 0) <= 0
            ]
            
            if removed:
                st.warning("**Removed Traits:** " + ", ".join(removed))
        
        # Editor & Visualization
        render_wordcloud(current_version["traits"])

        if st.session_state.get("show_editors", False):
            st.subheader("Trait Management")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Change traits**")
                # updates_text = deltas
                edited_updates = st.text_area(
                    "Edit via addition. trait: delta, subtract to 0 to remove",
                    value="",
                    height=300,
                    key="updates_editor"
                )
            
            with col2:
                st.markdown("**Current Traits**")
                current_text = char_data["history"][-1]["traits"].copy()
                edited_current = st.text_area(
                    "Edit current traits directly. trait: weight",
                    value=traits_to_text(current_text),
                    height=300,
                    key="traits_editor"
                )
            
            # --- Apply Changes Button ---
            if st.button("Apply Changes", key="apply_btn"):
                # Parse text areas
                updates = text_to_traits(edited_updates)
                current = text_to_traits(edited_current)
                
                # Apply updates to current traits
                for trait, delta in updates.items():
                    new_value = current.get(trait, 0) + delta
                    if new_value > 0:
                        current[trait] = new_value
                    elif trait in current:
                        del current[trait]
                
                # Update state
                st.session_state.current_traits = current
                st.session_state.pending_updates = {}
                
                # Update character data
                char_data["history"][-1]["traits"] = current
                save_character(char_data)
                st.success("Changes applied!")

                # Display changes
                edited_updates = ""
                edited_current = current


        # Character Analysis Section
        st.subheader("Character Analysis")

        # Initialize conversation history
        if "conversation" not in st.session_state:
            st.session_state.conversation = []

        # Sample prompt buttons
        st.write("Quick Analysis:")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Suggest Archetypes", key="archetype_btn"):
                st.session_state.custom_question = "What common character archetypes does this personality profile fit?"
        with col2:
            if st.button("Strengths & Flaws", key="flaws_btn"):
                st.session_state.custom_question = "Analyze key strengths and flaws based on these traits."
        with col3:
            if st.button("MBTI/Enneagram", key="arcs_btn"):
                st.session_state.custom_question = "What MBTI and Enneagram types are most likely for this character?"
        with col4:
            if st.button("Generate Opposite", key="opposite_btn"):
                st.session_state.custom_question = "Who would be the complete opposite of this character?"

        # Setting current question input
        current_question = st.text_area(
            "Ask about the character:", 
            height=100,
            key="current_question",
            placeholder="e.g., How would this character react to betrayal?",
            value=st.session_state.get("custom_question", "")
        )

        col1, col2 = st.columns(2)
        with col1:
            # Analysis display area
            if st.button("Ask Gemini", key="analyze_btn"):
                if current_question.strip():
                    current_traits = char_data["history"][-1]["traits"]
                    with st.spinner("Gemini is thinking..."):
                        try:
                            response = ask_question(
                                question=current_question,
                                name=selected_char,
                                traits=current_traits,
                                conversation_history=st.session_state.conversation
                            )
                            
                            # Add response to history
                            st.session_state.conversation.append({
                                "role": "user",
                                "content": current_question
                            })
                            st.session_state.conversation.append({
                                "role": "assistant",
                                "content": response
                            })
                            
                            # Clear input
                            st.session_state.custom_question = ""
                            st.rerun()  # Refresh to show new message
                            
                        except Exception as e:
                            st.error(f"Analysis failed: {str(e)}")
                else:
                    st.warning("Please enter a question")
        with col2:
            if st.button("Delete Chat History", key="clear_chat"):
                st.session_state.conversation = []  # Reset conversation history
                st.session_state.custom_question = "" # clear input field
                st.rerun()  # Refresh the UI immediately

        # Display conversation history
        chat_container = st.container()
        with chat_container:
            for msg in reversed(st.session_state.conversation):
                if not msg.get("content"):  # Skip empty messages
                    continue
                if msg["role"] == "user":
                    st.markdown(f"**User**: {msg['content']}")
                else:
                    st.markdown(f"**Gemini**: {msg['content']}")
                st.markdown("---")

if __name__ == "__main__":
    os.makedirs("characters", exist_ok=True)
    main()