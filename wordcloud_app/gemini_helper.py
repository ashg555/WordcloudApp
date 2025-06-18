from google import genai
import os
import re
import json
from dotenv import load_dotenv

load_dotenv()


def generate_traits(description, name, previous_weights="{empty}"):

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set or is empty.")
    client = genai.Client(api_key=api_key)

    prompt = f"""
Generate a JSON object containing adjustments to a fictional character's personality trait weights.
Example format:
{{
    "focused": 1, 
    "curious": 3, 
    "steady": 2, 
    ...
}}

Rules:
- weight_change can be a positive (stronger trait) or negative (weaker trait) integer that ADJUSTS the existing weights or adds a new trait.
- Only make small, reasonable shifts unless the description clearly contradicts a previous trait or emphasizes a new one strongly.
- Your changes will be added to the list to develop a nuanced personality over time.
- Refine existing traits by considering how new information reveals nuances, conditions, or interactions between traits. For example, a character might be 'confident' in public but 'insecure' privately.
- Preserve the shape of the character: treat prior traits as part of a growing, evolving profile.
- Include subtle synonym traits that expand meaning (e.g. both 'skeptical' and 'wary' if they express different sides). Include both emotional and behavioral traits where relevant.
- Keep traits to one or two words.

- Use the following scale for weight_change magnitude:
  - 1 to 2 for implied or subtle traits
  - 3 to 5 for directly stated or strongly implied traits
  - 6 or more ONLY if the trait is central, repeated, or heavily emphasized
  - Negative changes should follow the same logic, capped at -6 max
- Avoid large shifts unless the trait is clearly contradicted or reframed.
- Treat weight changes as minor adjustments to a stable profile—not a reset or redefinition.

Previous weights (for context):
{previous_weights}

New description for {name}:
{description}

Respond ONLY with the JSON object. No text or explanations.
    """

    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)

    print(f"""Description: {description}
Gemini Response: {response.text}
          """)

    return extract_json(response.text)


def ask_question(question, name, traits, conversation_history=[]):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set or is empty.")
    client = genai.Client(api_key=api_key)

    history_context = "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in conversation_history]
    )

    if len(history_context) > 0:
        prompt = f"""You are a creative writing assistant helping analyze a fictional character named {name} based on the following list of weighted personality traits:
{traits}

Conversation History:
{history_context}

Answer this new question in the context of our ongoing conversation.
Question: {question}
"""
    else:
        prompt = f"""You are a creative writing assistant helping analyze a fictional character named {name} based on the following list of weighted personality traits:
{traits}

Answer the following question based on the traits.

Question: {question}
"""
        
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    print("Prompt:", prompt, "\nResponse:", response.text)

    return response.text


def extract_json(text):
    """Extract JSON from Gemini response"""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}
