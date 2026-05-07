import anthropic
import csv
import os
from dotenv import load_dotenv

load_dotenv()
# Set up the connection to Claude
client = anthropic.Anthropic(
 api_key=os.environ.get("ANTHROPIC_API_KEY")   
)

# Read the listings CSV and turn each row into a readable description
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

# Read the firm info file
def load_firm_info():
    with open("firm_info.txt", "r") as f:
        return f.read()

# Load everything at startup
listings = load_listings()
firm_info = load_firm_info()

# Tell the agent who it is and what to do
system_prompt = f"""You are Riley, a friendly and knowledgeable assistant for Bay Area Premier Realty.

Your job is to help potential buyers learn about our listings and connect them with the right agent when they're ready.

How to behave:
- Be warm but professional, like a great concierge
- Keep responses concise unless asked for detail
- When showing a listing, highlight the 2-3 things that make it special, not every detail
- If someone seems interested in a property, offer to take their name and phone number for an agent to follow up
- If asked about something not in our info, say so honestly and offer to connect them with an agent
- Never discuss anything related to race, religion, family status, national origin, disability, or other protected classes when describing neighborhoods (Fair Housing Act compliance)
- If asked for advice on which listing is "best," ask what matters most to them (budget, size, location, schools, etc.) before recommending

=== FIRM INFO ===
{firm_info}

=== CURRENT LISTINGS ===
{listings}
"""

print("Real Estate Agent ready! Type 'quit' to exit.\n")

# Keep track of the conversation so the agent remembers what was said
conversation = []

while True:
    user_message = input("You: ")
    
    if user_message.lower() == "quit":
        print("Goodbye!")
        break
    
    if user_message.strip() == "":
        continue
    
    # Add the user's message to the conversation
    conversation.append({"role": "user", "content": user_message})
    
    # Send everything to Claude and get a response
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=conversation
    )
    
    # Get just the text part of the response
    assistant_message = response.content[0].text
    
    # Add the agent's reply to the conversation
    conversation.append({"role": "assistant", "content": assistant_message})
    
    print(f"\nAgent: {assistant_message}\n")