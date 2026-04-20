import chainlit as cl
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from fpdf import FPDF
from groq import Groq

# ---------------------------
# Load ENV
# ---------------------------
load_dotenv()

# ---------------------------
# Groq Setup
# ---------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"   # ✅ stable + free

# ---------------------------
# Data Setup
# ---------------------------
DATA_FILE = "data/projects.json"
os.makedirs("data", exist_ok=True)


if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)

# ---------------------------
# Save Project
# ---------------------------
def save_project(data):
    with open(DATA_FILE, "r+") as f:
        projects = json.load(f)
        projects.append(data)
        f.seek(0)
        json.dump(projects, f, indent=4)

# ---------------------------
# Clean Text (Fix PDF crash)
# ---------------------------
def clean_text(text):
    return re.sub(r'[^\x00-\xFF]+', '', text)

# ---------------------------
# Generate PDF
# ---------------------------
def generate_pdf(content, filename="brand_identity.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    content = clean_text(content)

    for line in content.split("\n"):
        pdf.multi_cell(0, 8, line)

    pdf.output(filename)
    return filename

# ---------------------------
# Groq API Call
# ---------------------------
def ask_groq(prompt):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional brand strategist. Do not use emojis. Be structured and detailed."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ---------------------------
# Chat Start
# ---------------------------
@cl.on_chat_start
async def start():
    cl.user_session.set("step", 0)
    cl.user_session.set("brand_data", {})

    await cl.Message(
        content="👋 Welcome to AI Brand Identity Assistant \n\nWhat is your brand name?"
    ).send()

# ---------------------------
# Chat Flow
# ---------------------------
@cl.on_message
async def main(message: cl.Message):
    step = cl.user_session.get("step")
    brand_data = cl.user_session.get("brand_data")

    # Step 0
    if step == 0:
        brand_data["name"] = message.content
        cl.user_session.set("step", 1)
        await cl.Message(content="🏢 What industry is your brand in?").send()

    # Step 1
    elif step == 1:
        brand_data["industry"] = message.content
        cl.user_session.set("step", 2)
        await cl.Message(content="🎯 Who is your target audience?").send()

    # Step 2
    elif step == 2:
        brand_data["audience"] = message.content
        cl.user_session.set("step", 3)
        await cl.Message(content="✨ Describe your brand personality").send()

    # Step 3 → Generate
    elif step == 3:
        brand_data["personality"] = message.content

        await cl.Message(content="⚡ Generating your brand identity...").send()

        prompt = f"""
        Create a complete and professional brand identity system.

        IMPORTANT:
        - Do NOT use emojis
        - Keep formatting clean and structured
        - Be specific, creative, and practical
        - Use bullet points where needed

        Brand Name: {brand_data['name']}
        Industry: {brand_data['industry']}
        Target Audience: {brand_data['audience']}
        Brand Personality: {brand_data['personality']}

        Provide the following:

        1. Brand Strategy
        - Mission Statement
        - Vision Statement
        - Core Values (3–5)
        - Unique Value Proposition
        - Brand Positioning

        2. Brand Personality & Archetype
        - Personality traits (e.g., bold, friendly, premium)
        - Brand archetype (e.g., Hero, Creator, Explorer)
        - Emotional tone

        3. Target Audience Insights
        - Demographics
        - Psychographics
        - Pain points
        - Buying behavior

        4. Color Palette
        - Primary Color (HEX + meaning)
        - Secondary Colors (HEX)
        - Accent Colors
        - Color usage guidelines

        5. Typography System
        - Heading Font (Google Font suggestion)
        - Body Font
        - Font pairing explanation
        - Usage hierarchy

        6. Logo Concepts
        - 3 logo ideas (detailed description)
        - Style direction (minimal, geometric, abstract, etc.)
        - Symbol meaning
        - Suggested layout (icon + text, wordmark, etc.)

        7. Visual Style Direction
        - Design style (modern, minimal, luxury, etc.)
        - Shapes and patterns
        - Icon style
        - Photography style

        8. Brand Voice & Messaging
        - Tone of voice (e.g., professional, playful)
        - Communication style
        - 5 tagline ideas
        - Example brand message

        9. Social Media Style
        - Post style ideas
        - Content themes
        - Caption tone
        - Visual consistency tips

        10. Brand Applications (Real-World Usage)
        - Business card concept
        - Website style direction
        - Packaging idea
        - Instagram feed concept

        11. Do's and Don'ts
        - What to do in branding
        - What to avoid

        Make the output highly structured and easy to read.
        """

        output = ask_groq(prompt)

        # Save
        project = {
            "timestamp": str(datetime.now()),
            "data": brand_data,
            "output": output
        }
        save_project(project)

        # PDF
        pdf_file = generate_pdf(output)

        # Send
        await cl.Message(content=output).send()

        await cl.Message(
            content="📄 Download your brand guideline:",
            elements=[cl.File(name="Brand_PDF", path=pdf_file)]
        ).send()

        cl.user_session.set("step", 4)

    else:
        await cl.Message(content="✅ Done! Restart to create another brand.").send()