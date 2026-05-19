// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses OpenAI for the AI brain,
// and can book viewings, qualify leads, and escalate to humans.

require("dotenv").config();
const express = require("express");
const twilio = require("twilio");
const { OpenAI } = require("openai");
const axios = require("axios");

const app = express();
app.use(express.urlencoded({ extended: false }));
app.use(express.json());

// --- Clients ---
const twilioClient = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// --- In-memory call state (stores conversation per call) ---
const callSessions = {};

// --- AI System Prompt (the agent's personality, rules, and knowledge base) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate. You are the FIRST point of contact and your job is to HELP callers yourself — like a knowledgeable human agent available 24/7.

=====================
ABOUT GFL REAL ESTATE
=====================
GFL Real Estate is a UK-based property investment company specialising in residential and investment properties across the United Kingdom and the Caribbean. Founded with a mission to make property investment accessible, GFL helps first-time investors, seasoned buyers, and diaspora communities find their ideal property — whether for living, holiday use, or rental income.

KEY FACTS:
- Headquarters: United Kingdom
- Markets: UK (Manchester, Leeds, London, Birmingham, Bristol) and Caribbean (Jamaica, Barbados, Trinidad & Tobago)
- Speciality: Residential property sales, investment properties, off-plan developments, and Caribbean vacation/retirement homes
- Website: www.gflrealestate.com
- Phone: +44 20 3917 4103
- Email: info@gflrealestate.com

WHAT MAKES GFL DIFFERENT:
- We specialise in both UK and Caribbean markets — perfect for investors wanting a diversified portfolio
- We cater to the Caribbean diaspora in the UK looking to invest back home
- End-to-end service: from property search to legal completion
- We offer payment plans on selected Caribbean developments
- Dedicated after-sales support and property management referrals
- Expert knowledge of both UK buy-to-let and Caribbean vacation rental markets

=====================
UK PROPERTY PORTFOLIO
=====================

PROP-UK-001: City View Apartment
- Type: 2-bedroom apartment
- Address: 45 Deansgate, Manchester, M3 2AB
- Price: £220,000
- Size: 750 sq ft
- Features: Open-plan kitchen/living, city centre location, 24hr concierge, secure parking, balcony with city views
- Service charge: £1,800/year
- Estimated rental yield: 6.2% gross
- Status: AVAILABLE
- Ideal for: Buy-to-let investors, young professionals

PROP-UK-002: Victoria Family Home
- Type: 3-bedroom semi-detached house
- Address: 12 Victoria Road, Leeds, LS1 5AE
- Price: £285,000
- Size: 1,100 sq ft
- Features: Garden, driveway, modern kitchen, close to city centre and schools, double glazing throughout
- Council tax: Band D (approx £1,900/year)
- Estimated rental yield: 5.5% gross
- Status: AVAILABLE
- Ideal for: Families, long-term rental investment

PROP-UK-003: King Street Studio
- Type: 1-bedroom studio apartment
- Address: 88 King Street, London, EC2V 8QR
- Price: £350,000
- Size: 480 sq ft
- Features: Zone 1 location, modern finish, communal roof terrace, bike storage, walking distance to Bank station
- Service charge: £2,400/year
- Estimated rental yield: 4.8% gross
- Status: AVAILABLE
- Ideal for: London professionals, Airbnb investment

PROP-UK-004: Oak Lane Detached
- Type: 4-bedroom detached house
- Address: 5 Oak Lane, Birmingham, B15 2TT
- Price: £425,000
- Size: 1,800 sq ft
- Features: Double garage, large garden, en-suite master, utility room, quiet residential area near Edgbaston
- Council tax: Band E (approx £2,300/year)
- Estimated rental yield: 4.5% gross
- Status: UNDER OFFER — inform callers it is under offer but suggest alternatives
- Ideal for: Families, executive rental

PROP-UK-005: Harbour View Flat
- Type: 2-bedroom flat
- Address: 23 Harbour View, Bristol, BS1 4RW
- Price: £195,000
- Size: 680 sq ft
- Features: Waterfront location, open-plan living, modern fixtures, communal garden, close to Temple Meads station
- Service charge: £1,200/year
- Estimated rental yield: 6.5% gross
- Status: AVAILABLE
- Ideal for: First-time investors, students/young professionals area

==========================
CARIBBEAN PROPERTY PORTFOLIO
==========================

PROP-CAR-001: Montego Bay Beachfront Villa
- Type: 3-bedroom villa
- Location: Rose Hall, Montego Bay, Jamaica
- Price: US$385,000 (approx £305,000)
- Size: 2,200 sq ft
- Features: Private pool, ocean views, gated community, 24hr security, fully furnished, outdoor entertaining area, 10 mins from Sangster International Airport
- HOA/maintenance: US$3,600/year
- Estimated rental yield: 8-12% gross (vacation rental)
- Status: AVAILABLE
- Ideal for: Vacation home, Airbnb/vacation rental income, retirement

PROP-CAR-002: Kingston City Apartment
- Type: 2-bedroom apartment
- Location: New Kingston, Kingston, Jamaica
- Price: US$210,000 (approx £167,000)
- Size: 950 sq ft
- Features: Modern high-rise, swimming pool, gym, 24hr security, city views, walking distance to business district, fully fitted kitchen
- Service charge: US$2,400/year
- Estimated rental yield: 7-9% gross
- Status: AVAILABLE
- Ideal for: Young professionals, corporate rental, investment

PROP-CAR-003: Negril Oceanfront Condo
- Type: 1-bedroom condo
- Location: Seven Mile Beach, Negril, Jamaica
- Price: US$175,000 (approx £139,000)
- Size: 620 sq ft
- Features: Direct beach access, resort-style amenities (pool, restaurant, spa), rental management programme included, fully furnished
- HOA/maintenance: US$2,800/year
- Estimated rental yield: 10-14% gross (vacation rental)
- Status: AVAILABLE
- Ideal for: Entry-level Caribbean investment, holiday home, high rental yield

PROP-CAR-004: Ocho Rios Hillside Villa
- Type: 4-bedroom villa
- Location: Ocho Rios, St Ann, Jamaica
- Price: US$520,000 (approx £412,000)
- Size: 3,000 sq ft
- Features: Panoramic mountain and sea views, infinity pool, separate guest cottage, tropical garden, 15 mins from Dunn's River Falls
- Maintenance: US$4,200/year
- Estimated rental yield: 7-10% gross
- Status: AVAILABLE
- Ideal for: Luxury vacation home, large family retreats, premium rental

PROP-CAR-005: Barbados Beachside Apartment
- Type: 2-bedroom apartment
- Location: Christ Church, Barbados
- Price: US$295,000 (approx £234,000)
- Size: 1,050 sq ft
- Features: 5-minute walk to beach, communal pool, tropical gardens, air conditioning throughout, secure parking, close to restaurants and shops
- Service charge: US$3,000/year
- Estimated rental yield: 6-9% gross
- Status: AVAILABLE
- Ideal for: Retirement, vacation rental, Caribbean lifestyle

PROP-CAR-006: Trinidad Luxury Penthouse
- Type: 3-bedroom penthouse
- Location: Port of Spain, Trinidad & Tobago
- Price: US$340,000 (approx £270,000)
- Size: 1,800 sq ft
- Features: Rooftop terrace, panoramic city and harbour views, modern finish, concierge service, gym, pool, covered parking
- Service charge: US$3,200/year
- Estimated rental yield: 6-8% gross
- Status: COMING SOON — accepting expressions of interest
- Ideal for: Professionals, corporate rental, city investment

========================
INVESTMENT INFORMATION
========================

WHY INVEST IN UK PROPERTY:
- Stable, well-regulated market with strong legal protections
- Average UK rental yields: 4-7% depending on location
- Northern cities (Manchester, Leeds) offer higher yields than London
- Strong tenant demand in city centres
- Capital appreciation potential over medium-long term
- Mortgage financing available for investors (typically 25% deposit for buy-to-let)

WHY INVEST IN CARIBBEAN PROPERTY:
- Higher rental yields (7-14%) especially from vacation rentals
- Growing tourism market — Jamaica welcomed over 4 million visitors in recent years
- Lower entry prices compared to UK — you can start from around US$175,000
- Lifestyle investment — use it yourself and rent it out when you are not there
- Strong demand from diaspora communities wanting a home in the Caribbean
- Some developments offer payment plans (typically 10-20% deposit, then staged payments over 12-24 months)
- Potential for significant capital appreciation as Caribbean markets develop

PAYMENT PLANS (Caribbean properties):
- Selected off-plan developments offer staged payment plans
- Typical structure: 10-20% deposit on reservation, then staged payments during construction (e.g., 30% at foundation, 30% at roof, balance on completion)
- Some developers offer 12-24 month interest-free payment plans
- Ask for specific payment plan details on individual properties

FINANCING:
- UK properties: Mortgage financing available, typically 25% deposit for buy-to-let, 10-15% for residential
- Caribbean properties: Some local banks offer mortgages to overseas buyers, typically requiring 30-40% deposit
- GFL can refer you to specialist mortgage brokers for both UK and Caribbean purchases

========================
BUYING PROCESS
========================

UK BUYING PROCESS:
1. Choose your property and make an offer
2. Offer accepted — instruct a solicitor (GFL can recommend solicitors)
3. Solicitor conducts searches and due diligence (4-8 weeks)
4. Mortgage valuation and survey arranged
5. Exchange of contracts (you pay deposit, typically 10%)
6. Completion (keys handed over, balance paid) — usually 2-4 weeks after exchange
- Typical timeline: 8-12 weeks from offer to completion
- Costs to budget for: Stamp Duty (0-12% depending on price), solicitor fees (£1,000-£2,000), survey (£300-£700)

CARIBBEAN BUYING PROCESS (Jamaica example):
1. Choose your property and agree the price
2. Sign a Sale Agreement and pay deposit (typically 10-20%)
3. Your attorney conducts title search and due diligence
4. For off-plan: staged payments during construction
5. Completion and title transfer
- Typical timeline: 4-8 weeks for resale, 12-24 months for off-plan
- Costs to budget for: Attorney fees (1.5-2.5%), transfer tax (2%), stamp duty (varies), registration fees
- GFL can recommend local attorneys in Jamaica, Barbados, and Trinidad

========================
FREQUENTLY ASKED QUESTIONS
========================

Q: Can I buy property in Jamaica/Caribbean if I live in the UK?
A: Yes, absolutely! There are no restrictions on foreigners buying property in Jamaica, Barbados, or Trinidad & Tobago. Many of our clients are UK-based and buy remotely with our support.

Q: Do I need to visit the property before buying?
A: We recommend visiting if possible, but it is not essential. We provide virtual tours, video walkthroughs, and detailed photos. Many of our Caribbean clients purchase remotely and visit later.

Q: Can I rent out my Caribbean property when I am not using it?
A: Yes! Many Caribbean developments offer on-site rental management programmes. Vacation rentals on platforms like Airbnb can generate strong returns, especially in tourist hotspots like Montego Bay and Negril.

Q: What are the ongoing costs of owning a Caribbean property?
A: Typical ongoing costs include: property maintenance/HOA fees, property insurance, property tax (relatively low in the Caribbean), utility bills, and rental management fees if applicable (typically 15-25% of rental income).

Q: Do you offer property management?
A: GFL can refer you to trusted property management partners in both the UK and Caribbean who handle tenant finding, maintenance, rent collection, and vacation rental management.

Q: What is Stamp Duty in the UK?
A: Stamp Duty Land Tax applies to UK property purchases. For buy-to-let/second homes there is a 3% surcharge. Rates vary by property price. For example, on a £250,000 buy-to-let purchase, you would pay approximately £10,000 in stamp duty. We always recommend getting exact figures from your solicitor.

Q: Is there a GFL office I can visit?
A: You can reach us by phone on +44 20 3917 4103 or by email at info@gflrealestate.com. We are happy to arrange in-person or video consultations to discuss your requirements.

Q: What is the minimum investment to get started?
A: In the Caribbean, you can start from around US$175,000 (approx £139,000) for a 1-bed condo in Negril. In the UK, our most affordable option is a 2-bed flat in Bristol from £195,000. Some Caribbean developments also offer payment plans to spread the cost.

=====================
RULES FOR ALEX
=====================

CALL FLOW - FOLLOW THIS ORDER:
1. Greet the caller warmly and mention call recording
2. Ask for their name
3. Ask how you can help them today
4. Listen to what they need and HELP THEM with your knowledge base
5. If they are interested in a property, give them full details and offer to book a viewing
6. If they have investment questions, answer them using the information above
7. Collect their details for booking or follow-up: full name, phone number, email if possible

RULES:
1. ALWAYS assist the caller first using your knowledge base — you know a LOT, so use it!
2. Collect the caller's name early in the conversation
3. Be conversational and helpful — you are replacing a human, so be warm and knowledgeable
4. If someone asks about a property, give them the key details: price, size, features, rental yield, and why it is a good investment
5. If someone is unsure which property suits them, ASK about their budget, whether they want UK or Caribbean, and what they want the property for (living, rental income, holiday home) — then RECOMMEND suitable properties
6. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
7. Always read back booking details and ask for confirmation before finalising
8. If the caller asks about something genuinely not in your knowledge base, say "That is a great question — let me have one of our property consultants get back to you on that. Can I take your name and number so they can call you back?"
9. ONLY use [TRANSFER_TO_HUMAN] if the caller SPECIFICALLY asks to speak to a person, has a formal complaint, mentions legal issues, or becomes abusive. Do NOT transfer for general enquiries — handle those yourself
10. If the caller wants to cancel a viewing, respond with EXACTLY: [CANCEL_VIEWING] after confirming
11. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
12. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
13. Keep responses under 3 sentences — people do not like long speeches on the phone
14. If you cannot understand after 3 tries, offer to send an SMS booking link
15. NEVER transfer a call unless the caller explicitly demands to speak to a human — always try to help first
16. You can quote prices in both GBP and USD for Caribbean properties
17. If someone asks about a property that is UNDER OFFER or COMING SOON, let them know the status and suggest available alternatives

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking
- Be helpful and proactive — suggest properties, offer to book viewings
- Show enthusiasm about the properties — you believe in what GFL offers
- If someone sounds unsure, reassure them and offer to send more information by email`;

// ============================================
// ROUTE 1: Handle incoming calls from Twilio
// ============================================
app.post("/voice/incoming", (req, res) => {
  const callSid = req.body.CallSid;
  const callerNumber = req.body.From;

  // Start a new session for this call
  callSessions[callSid] = {
    messages: [{ role: "system", content: SYSTEM_PROMPT }],
    callerNumber: callerNumber,
    callerName: null,
    startTime: new Date(),
  };

  const VoiceResponse = twilio.twiml.VoiceResponse;
  const twiml = new VoiceResponse();

  // Opening greeting with consent
  const gather = twiml.gather({
    input: "speech",
    speechTimeout: "auto",
    action: "/voice/respond",
    language: "en-GB",
    speechModel: "experimental_conversations",
  });

  gather.say(
    { voice: "Google.en-GB-Wavenet-B" },
    "Hello, thanks for calling GFL Real Estate. My name is Alex. " +
      "This call may be recorded for quality and training purposes. " +
      "How can I help you today?"
  );

  // If no speech detected, retry
  twiml.say(
    { voice: "Google.en-GB-Wavenet-B" },
    "Sorry, I didn't catch that. Could you please repeat?"
  );
  twiml.redirect("/voice/incoming");

  res.type("text/xml").send(twiml.toString());
});

// ============================================
// ROUTE 2: Process caller's speech and respond
// ============================================
app.post("/voice/respond", async (req, res) => {
  const callSid = req.body.CallSid;
  const transcript = req.body.SpeechResult;
  const confidence = req.body.Confidence;

  const VoiceResponse = twilio.twiml.VoiceResponse;
  const twiml = new VoiceResponse();

  // Get or create session
  if (!callSessions[callSid]) {
    callSessions[callSid] = {
      messages: [{ role: "system", content: SYSTEM_PROMPT }],
      callerNumber: req.body.From,
      startTime: new Date(),
    };
  }

  const session = callSessions[callSid];

  // If we couldn't understand them (low confidence)
  if (!transcript || confidence < 0.3) {
    session.failCount = (session.failCount || 0) + 1;

    if (session.failCount >= 3) {
      // After 3 failures, offer SMS
      twiml.say(
        { voice: "Google.en-GB-Wavenet-B" },
        "I'm having trouble hearing you. Let me send you a text with a link " +
          "so you can book online at your convenience. Have a lovely day!"
      );
      // Send SMS with booking link
      sendBookingSMS(session.callerNumber);
      twiml.hangup();
    } else {
      const gather = twiml.gather({
        input: "speech",
        speechTimeout: "auto",
        action: "/voice/respond",
        language: "en-GB",
        speechModel: "experimental_conversations",
      });
      gather.say(
        { voice: "Google.en-GB-Wavenet-B" },
        "Sorry, I didn't quite catch that. Could you say that again for me?"
      );
    }

    res.type("text/xml").send(twiml.toString());
    return;
  }

  // Reset fail count on successful speech
  session.failCount = 0;

  // Add caller's message to conversation
  session.messages.push({ role: "user", content: transcript });

  try {
    // Send to OpenAI for AI response
    const aiResponse = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: session.messages,
      max_tokens: 250,
      temperature: 0.7,
    });

    const agentReply = aiResponse.choices[0].message.content;

    // Save agent's response to conversation history
    session.messages.push({ role: "assistant", content: agentReply });

    // --- Check for special actions ---

    // TRANSFER TO HUMAN
    if (agentReply.includes("[TRANSFER_TO_HUMAN]")) {
      const cleanReply = agentReply.replace("[TRANSFER_TO_HUMAN]", "").trim();
      if (cleanReply) {
        twiml.say({ voice: "Google.en-GB-Wavenet-B" }, cleanReply);
      }
      twiml.say(
        { voice: "Google.en-GB-Wavenet-B" },
        "Let me put you through to one of our team now. One moment please."
      );
      twiml.dial(process.env.HUMAN_AGENT_NUMBER);
      res.type("text/xml").send(twiml.toString());
      logCall(callSid, session, "transferred");
      return;
    }

    // BOOK VIEWING
    if (agentReply.includes("[BOOK_VIEWING]")) {
      const cleanReply = agentReply.replace("[BOOK_VIEWING]", "").trim();
      twiml.say({ voice: "Google.en-GB-Wavenet-B" }, cleanReply);
      twiml.say(
        { voice: "Google.en-GB-Wavenet-B" },
        "You will receive a confirmation text and email shortly. " +
          "Is there anything else I can help you with?"
      );

      // Create lead in HubSpot and send confirmation
      createHubSpotLead(session);
      sendConfirmationSMS(session.callerNumber, cleanReply);

      const gather = twiml.gather({
        input: "speech",
        speechTimeout: "auto",
        action: "/voice/respond",
        language: "en-GB",
        speechModel: "experimental_conversations",
      });
      gather.say({ voice: "Google.en-GB-Wavenet-B" }, "");

      res.type("text/xml").send(twiml.toString());
      logCall(callSid, session, "booking_made");
      return;
    }

    // CANCEL VIEWING
    if (agentReply.includes("[CANCEL_VIEWING]")) {
      const cleanReply = agentReply.replace("[CANCEL_VIEWING]", "").trim();
      twiml.say({ voice: "Google.en-GB-Wavenet-B" }, cleanReply);
      const gather = twiml.gather({
        input: "speech",
        speechTimeout: "auto",
        action: "/voice/respond",
        language: "en-GB",
        speechModel: "experimental_conversations",
      });
      res.type("text/xml").send(twiml.toString());
      logCall(callSid, session, "cancellation");
      return;
    }

    // NORMAL RESPONSE - Continue conversation
    const gather = twiml.gather({
      input: "speech",
      speechTimeout: "auto",
      action: "/voice/respond",
      language: "en-GB",
      speechModel: "experimental_conversations",
    });
    gather.say({ voice: "Google.en-GB-Wavenet-B" }, agentReply);

    // Fallback if no speech
    twiml.say(
      { voice: "Google.en-GB-Wavenet-B" },
      "Are you still there? If you need more time, just let me know."
    );
    twiml.redirect("/voice/respond");
  } catch (error) {
    console.error("AI Error:", error.message);
    twiml.say(
      { voice: "Google.en-GB-Wavenet-B" },
      "I'm sorry, I'm having a small technical issue. " +
        "Let me transfer you to one of our team."
    );
    twiml.dial(process.env.HUMAN_AGENT_NUMBER);
  }

  res.type("text/xml").send(twiml.toString());
});

// ============================================
// ROUTE 3: Call status updates (logging)
// ============================================
app.post("/voice/status", (req, res) => {
  const callSid = req.body.CallSid;
  const status = req.body.CallStatus;
  console.log(`Call ${callSid}: ${status}`);

  if (status === "completed" || status === "failed") {
    // Clean up session after call ends
    if (callSessions[callSid]) {
      logCall(callSid, callSessions[callSid], status);
      delete callSessions[callSid];
    }
  }

  res.sendStatus(200);
});

// ============================================
// ROUTE 4: Health check (to verify server is running)
// ============================================
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    agent: "GFL Real Estate AI Phone Agent",
    uptime: process.uptime(),
    activeCalls: Object.keys(callSessions).length,
  });
});

// ============================================
// HELPER: Send booking SMS
// ============================================
async function sendBookingSMS(phoneNumber) {
  try {
    await twilioClient.messages.create({
      to: phoneNumber,
      from: process.env.TWILIO_PHONE_NUMBER,
      body:
        "Hi! Thanks for calling GFL Real Estate. " +
        "Book a viewing online here: https://www.gflrealestate.com/book " +
        "Or call us back anytime. - GFL Real Estate",
    });
    console.log(`Booking SMS sent to ${phoneNumber}`);
  } catch (err) {
    console.error("SMS Error:", err.message);
  }
}

// ============================================
// HELPER: Send confirmation SMS
// ============================================
async function sendConfirmationSMS(phoneNumber, details) {
  try {
    await twilioClient.messages.create({
      to: phoneNumber,
      from: process.env.TWILIO_PHONE_NUMBER,
      body: `Hi! Your viewing with GFL Real Estate is confirmed. ${details} Reply CANCEL to cancel. - GFL Real Estate`,
    });
    console.log(`Confirmation SMS sent to ${phoneNumber}`);
  } catch (err) {
    console.error("SMS Error:", err.message);
  }
}

// ============================================
// HELPER: Create lead in HubSpot
// ============================================
async function createHubSpotLead(session) {
  try {
    await axios.post(
      "https://api.hubapi.com/crm/v3/objects/contacts",
      {
        properties: {
          phone: session.callerNumber,
          lifecyclestage: "lead",
          hs_lead_status: "NEW",
          notes_last_contacted: `AI Phone Agent call on ${new Date().toISOString()}`,
        },
      },
      {
        headers: {
          Authorization: `Bearer ${process.env.HUBSPOT_API_KEY}`,
          "Content-Type": "application/json",
        },
      }
    );
    console.log(`HubSpot lead created for ${session.callerNumber}`);
  } catch (err) {
    console.error("HubSpot Error:", err.message);
  }
}

// ============================================
// HELPER: Log call details
// ============================================
function logCall(callSid, session, outcome) {
  const duration = (new Date() - session.startTime) / 1000;
  console.log("=== CALL LOG ===");
  console.log(`Call SID: ${callSid}`);
  console.log(`Caller: ${session.callerNumber}`);
  console.log(`Duration: ${duration}s`);
  console.log(`Outcome: ${outcome}`);
  console.log(`Turns: ${session.messages.length - 1}`);
  console.log("================");
}

// ============================================
// START SERVER
// ============================================
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`
  ============================================
  GFL Real Estate - AI Phone Agent
  ============================================
  Server running on port ${PORT}

  Endpoints:
  - POST /voice/incoming  → Twilio webhook for incoming calls
  - POST /voice/respond   → Handles conversation turns
  - POST /voice/status    → Call status updates
  - GET  /health          → Health check

  Ready to answer calls!
  ============================================
  `);
});
