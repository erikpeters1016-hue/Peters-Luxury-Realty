from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic
import csv
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import resend
import gspread
from google.oauth2.service_account import Credentials
load_dotenv()
resend.api_key = os.environ.get("RESEND_API_KEY")
# Set up the Flask app — this is our web server
app = Flask(__name__)
CORS(app)  # Allow the browser to talk to this server

# Set up the connection to Claude
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

# Same listing-loading function as before
def load_listings():
    listings_text = ""
    with open("listings.csv", "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            listings_text += f"""
LISTING {i}
Address: {row['address']}, {row['city']}, CA
Price: ${int(row['price']):,}
Bedrooms: {row['bedrooms']}
Bathrooms: {row['bathrooms']}
Square Feet: {row['sqft']}
Year Built: {row['year_built']}
Features: {row['features']}
School District: {row['school_district']}
HOA: {row['hoa']}
Notes: {row['notes']}
"""
    return listings_text

def load_firm_info():
    with open("firm_info.txt", "r") as f:
        return f.read()

# Load everything once at startup
listings = load_listings()
firm_info = load_firm_info()

# Tell the agent who it is and what to do
system_prompt = f"""You are Riley, a warm and knowledgeable concierge for Peters Luxury Realty, a boutique luxury real estate firm serving Beverly Hills, Bel Air, Malibu, and the Hollywood Hills.

# Your role
You help potential buyers explore listings, answer questions about neighborhoods and the buying process, and connect serious leads with a human agent.

# Tone
- - Polished, gracious, discreet — like a concierge at a five-star hotel
- Conversational and warm, never stiff, never salesy
- Confident and knowledgeable about the LA luxury market
- Calm pacing — quality over quantity in every response
- Match the user's energy: brief if they're brief, detailed if they want 
depth
- Light, tasteful use of emojis is fine occasionally (🏛️ ✨ 👋), but don't overdo it

# Formatting
- Use **bold** for property addresses, prices, and key facts
- Use bullet lists for property features (3-5 bullets max, the highlights only)
- Keep responses tight — usually 2-5 short paragraphs or a short list
- Don't dump every detail; tease the best parts and offer to share more

# When showing a listing
Lead with what makes it special, not a data sheet. Example structure:
"**456 Pine Avenue in Berkeley** is a stunner — **$1,250,000**, 4 bed / 3 bath with bay views and solar panels. It's also close to UC Berkeley, which buyers in that price range often love."

Then offer a next step: "Want me to tell you more, or set you up with our agent for a private showing?"


# Qualifying interest
When someone seems genuinely interested in a property, gently learn what matters to them. Good questions to weave in naturally:
- What's their timeline?
- Are they cash buyers, or working with a lender? (Many luxury buyers are cash.)
- Do they have proof of funds available? (Standard for luxury showings.)
- What brings them to LA — primary residence, second home, or investment?
- Any must-haves (privacy level, view, beachfront, gated estate, etc.)?

Don't ask all at once. One or two at a time, conversationally. Be respectful — luxury buyers are often discerning and may not want to share everything upfront.

# Lead capture
If a user shares their name, phone number, or email, acknowledge it warmly and confirm:
"Got it — I'll let our agent know to reach out to [name] at [number] within the next few hours during business hours. In the meantime, anything else I can answer?"

If they show strong interest but haven't shared contact info, offer the option:
"Would you like an agent to reach out? Just share your name and best number."

Never claim an agent will follow up unless the user has actually shared contact info.

# What you don't know
If asked something not in our info (specific square footage of a room, exact lot size, HOA bylaws, etc.), be honest:
"I don't have that detail, but our agent can pull it up quickly. Want me to have someone reach out?"

# Fair Housing compliance — important
Never discuss neighborhoods in terms of:
- Race, ethnicity, or national origin
- Religion
- Family status (kids/no kids, families vs. singles)
- Disability
- "Safe" or "unsafe" (subjective, can imply protected class)

If asked something like "is this a good neighborhood for families?" or "is it safe?", redirect warmly:
"For neighborhood specifics like that, our agents share local crime statistics, school ratings, and community resources so you can decide what's the right fit for you. Want me to set up a chat?"

# Small talk
You can briefly engage with friendly small talk ("how's your day", "thanks", etc.) but always pivot back to how you can help with their home search.

# Never
- Make up listing details
- Quote prices or features that aren't in the data
- Promise specific availability or showing times — that's the agent's job
- Discuss other firms or compare prices to competitors

=== FIRM INFO ===
{firm_info}

=== CURRENT LISTINGS ===
{listings}
"""
# ──────────────────────────────────────────────────────────────
# LEAD CAPTURE
# ──────────────────────────────────────────────────────────────

def extract_lead_info(conversation):
    """Use Claude to check if the customer has shared their name + contact info."""
    
    # Build a readable transcript
    transcript = ""
    for msg in conversation:
        role = "Customer" if msg["role"] == "user" else "Riley"
        transcript += f"{role}: {msg['content']}\n"
    
    extraction_prompt = f"""Analyze this real estate chat. Has the customer shared BOTH:
1. Their name (first name minimum)
2. A phone number OR email address

If BOTH are present, respond with valid JSON only (no other text, no markdown):
{{"lead": true, "name": "their full name", "contact": "phone or email", "interest": "1-sentence summary of what they want"}}

If either is missing, respond with valid JSON only:
{{"lead": false}}

Conversation:
{transcript}

Respond with ONLY the JSON, no explanation."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": extraction_prompt}]
        )
        result_text = response.content[0].text.strip()
        # Strip markdown code fences if Claude added them
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        result = json.loads(result_text)
        return result
    except Exception as e:
        print(f"Lead extraction error: {e}")
        return {"lead": False}


def already_saved(name, contact):
    """Check if this lead has already been saved (avoids duplicate entries during a single chat)."""
    if not os.path.exists("leads.csv"):
        return False
    with open("leads.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("name") == name and row.get("contact") == contact:
                return True
    return False


def send_lead_email(name, contact, interest, conversation):
    """Email a lead notification to the firm's lead inbox."""
    
    notification_email = os.environ.get("LEAD_NOTIFICATION_EMAIL")
    if not notification_email:
        print("⚠️  No LEAD_NOTIFICATION_EMAIL set — skipping email")
        return
    
    # Build a readable HTML transcript of the conversation
    transcript_html = ""
    for msg in conversation:
        role = "Customer" if msg["role"] == "user" else "Riley"
        bg_color = "#f5f0e8" if msg["role"] == "user" else "#ffffff"
        transcript_html += f"""
        <div style="background:{bg_color};padding:12px 16px;border-radius:12px;margin-bottom:8px;border:1px solid #e2e8f0;">
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#888;margin-bottom:4px;">{role}</div>
            <div style="color:#2d3748;line-height:1.5;">{msg['content']}</div>
        </div>
        """
    
    html_body = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:600px;margin:0 auto;padding:24px;color:#2d3748;">
        <div style="background:linear-gradient(135deg,#2a2520 0%,#1a1612 100%);color:white;padding:24px;border-radius:12px 12px 0 0;">
            <div style="font-family:'Georgia',serif;font-size:24px;font-weight:500;margin-bottom:4px;">🏛️ New Lead — Peters Luxury Realty</div>
            <div style="font-size:13px;opacity:0.85;">Captured by Riley · {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</div>
        </div>
        
        <div style="background:white;padding:24px;border-radius:0 0 12px 12px;border:1px solid #e2e8f0;border-top:none;">
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:8px 0;color:#888;font-size:13px;width:120px;">NAME</td><td style="padding:8px 0;font-size:16px;font-weight:600;">{name}</td></tr>
                <tr><td style="padding:8px 0;color:#888;font-size:13px;">CONTACT</td><td style="padding:8px 0;font-size:16px;">{contact}</td></tr>
                <tr><td style="padding:8px 0;color:#888;font-size:13px;vertical-align:top;">INTEREST</td><td style="padding:8px 0;font-size:15px;line-height:1.5;">{interest}</td></tr>
            </table>
            
            <div style="background:#f5f0e8;padding:14px;border-radius:8px;margin-top:20px;border-left:3px solid #d4af6c;">
                <strong style="color:#2a2520;">⚡ Speed-to-lead matters.</strong> Studies show calling within 5 minutes is 100x more effective than within an hour. Reach out now.
            </div>
            
            <h3 style="margin-top:32px;margin-bottom:12px;font-family:Georgia,serif;font-weight:500;color:#2a2520;">Conversation Transcript</h3>
            {transcript_html}
        </div>
        
        <div style="text-align:center;color:#888;font-size:11px;margin-top:16px;">Powered by Riley · Peters Luxury Realty AI Concierge</div>
    </div>
    """
    
    try:
        resend.Emails.send({
            "from": "Riley <onboarding@resend.dev>",
            "to": [notification_email],
            "subject": f"🏛️ New Lead: {name} ({contact})",
            "html": html_body
        })
        print(f"📧 Lead email sent to {notification_email}")
    except Exception as e:
        print(f"⚠️  Email error: {e}")

def append_to_google_sheet(name, contact, interest, conversation):
    """Append a new lead row to the connected Google Sheet."""
    
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("⚠️  No GOOGLE_SHEET_ID set — skipping Sheets")
        return
    
    try:
        # Authenticate with the service account (works both locally and on Render)
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        
        # Try env var first (production), then fall back to file (local)
        creds_json_string = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json_string:
            creds_dict = json.loads(creds_json_string)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            creds = Credentials.from_service_account_file("google-credentials.json", scopes=scopes)
        
        client_gs = gspread.authorize(creds)
        sheet = client_gs.open_by_key(sheet_id).sheet1
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name,
            contact,
            interest,
            "New",
            "Website chat (Riley)",
            ""
        ])
        print(f"📊 Lead added to Google Sheet")
    except Exception as e:
        print(f"⚠️  Google Sheets error: {e}")       

def save_lead(name, contact, interest, conversation):
    """Append a new lead to leads.csv. Creates the file with headers if it doesn't exist."""
    
    if already_saved(name, contact):
        return False
    
    file_exists = os.path.exists("leads.csv")
    
    transcript = ""
    for msg in conversation:
        role = "Customer" if msg["role"] == "user" else "Riley"
        transcript += f"{role}: {msg['content']}\n\n"
    
    with open("leads.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "name", "contact", "interest", "transcript"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name,
            contact,
            interest,
            transcript
        ])
    print(f"💾 NEW LEAD SAVED: {name} ({contact}) — {interest}")
    send_lead_email(name, contact, interest, conversation)
    append_to_google_sheet(name, contact, interest, conversation)
    return True
# This is a "route" — when the browser visits the main page (/), serve up index.html
@app.route("/")
def home():
    return send_from_directory(".", "index.html")


# This is the API endpoint — the browser will send messages here
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    conversation = data.get("conversation", [])
    
    # Get Riley's response
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=conversation
    )
    assistant_message = response.content[0].text
    
    # Build full conversation including Riley's new reply
    full_conversation = conversation + [{"role": "assistant", "content": assistant_message}]
    
    # Run lead detection in the background of the conversation
    lead_info = extract_lead_info(full_conversation)
    if lead_info.get("lead"):
        save_lead(
            name=lead_info.get("name", "Unknown"),
            contact=lead_info.get("contact", "Unknown"),
            interest=lead_info.get("interest", ""),
            conversation=full_conversation
        )
    
    return jsonify({"reply": assistant_message})
   

# Start the server when we run this file
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Server starting at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)