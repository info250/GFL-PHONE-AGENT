// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses Deepgram for speech-to-text, OpenAI for the AI brain,
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

// --- AI System Prompt (the agent's personality and rules) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate, a property investment company based in the UK.

YOUR ROLE:
- Answer inbound customer calls warmly and professionally
- Help callers with property enquiries (prices, details, availability)
- Book, reschedule, or cancel property viewings
- Qualify leads by collecting: name, phone number, email, budget range, property interest
- Escalate to a human agent when needed

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking

RULES:
1. At the start of every call, greet the caller and mention call recording
2. Collect the caller's name early in the conversation
3. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
4. Always read back booking details and ask for confirmation before finalising
5. If the caller asks about something you don't know, say "Let me have someone from the team get back to you on that"
6. If the caller asks to speak to a person, says they have a complaint, mentions legal issues, or becomes abusive, respond with EXACTLY: [TRANSFER_TO_HUMAN]
7. If the caller wants to cancel, respond with EXACTLY: [CANCEL_VIEWING] after confirming
8. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
9. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
10. Keep responses under 3 sentences - people don't like long speeches on the phone
11. If you can't understand after 3 tries, offer to send an SMS booking link

AVAILABLE PROPERTIES (use these for enquiries):
- PROP-001: 2-bed apartment, 45 Deansgate, Manchester, M3 2AB - £220,000 - Service charge £1,800/yr - Available
- PROP-002: 3-bed house, 12 Victoria Road, Leeds, LS1 5AE - £285,000 - Council tax Band D - Available
- PROP-003: 1-bed studio, 88 King Street, London, EC2V 8QR - £350,000 - Service charge £2,400/yr - Available
- PROP-004: 4-bed detached, 5 Oak Lane, Birmingham, B15 2TT - £425,000 - Council tax Band E - Under Offer
- PROP-005: 2-bed flat, 23 Harbour View, Bristol, BS1 4RW - £195,000 - Service charge £1,200/yr - Available

When PROP-004 is asked about, let them know it's currently under offer but suggest similar alternatives.`;

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
      max_tokens: 200,
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
    // Extract name from conversation if available
    const conversation = session.messages
      .filter((m) => m.role !== "system")
      .map((m) => m.content)
      .join(" ");

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
});// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses Deepgram for speech-to-text, OpenAI for the AI brain,
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

// --- AI System Prompt (the agent's personality and rules) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate, a property investment company based in the UK.

YOUR ROLE:
- Answer inbound customer calls warmly and professionally
- Help callers with property enquiries (prices, details, availability)
- Book, reschedule, or cancel property viewings
- Qualify leads by collecting: name, phone number, email, budget range, property interest
- Escalate to a human agent when needed

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking

RULES:
1. At the start of every call, greet the caller and mention call recording
2. Collect the caller's name early in the conversation
3. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
4. Always read back booking details and ask for confirmation before finalising
5. If the caller asks about something you don't know, say "Let me have someone from the team get back to you on that"
6. If the caller asks to speak to a person, says they have a complaint, mentions legal issues, or becomes abusive, respond with EXACTLY: [TRANSFER_TO_HUMAN]
7. If the caller wants to cancel, respond with EXACTLY: [CANCEL_VIEWING] after confirming
8. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
9. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
10. Keep responses under 3 sentences - people don't like long speeches on the phone
11. If you can't understand after 3 tries, offer to send an SMS booking link

AVAILABLE PROPERTIES (use these for enquiries):
- PROP-001: 2-bed apartment, 45 Deansgate, Manchester, M3 2AB - £220,000 - Service charge £1,800/yr - Available
- PROP-002: 3-bed house, 12 Victoria Road, Leeds, LS1 5AE - £285,000 - Council tax Band D - Available
- PROP-003: 1-bed studio, 88 King Street, London, EC2V 8QR - £350,000 - Service charge £2,400/yr - Available
- PROP-004: 4-bed detached, 5 Oak Lane, Birmingham, B15 2TT - £425,000 - Council tax Band E - Under Offer
- PROP-005: 2-bed flat, 23 Harbour View, Bristol, BS1 4RW - £195,000 - Service charge £1,200/yr - Available

When PROP-004 is asked about, let them know it's currently under offer but suggest similar alternatives.`;

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
      max_tokens: 200,
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
    // Extract name from conversation if available
    const conversation = session.messages
      .filter((m) => m.role !== "system")
      .map((m) => m.content)
      .join(" ");

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
});// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses Deepgram for speech-to-text, OpenAI for the AI brain,
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

// --- AI System Prompt (the agent's personality and rules) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate, a property investment company based in the UK.

YOUR ROLE:
- Answer inbound customer calls warmly and professionally
- Help callers with property enquiries (prices, details, availability)
- Book, reschedule, or cancel property viewings
- Qualify leads by collecting: name, phone number, email, budget range, property interest
- Escalate to a human agent when needed

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking

RULES:
1. At the start of every call, greet the caller and mention call recording
2. Collect the caller's name early in the conversation
3. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
4. Always read back booking details and ask for confirmation before finalising
5. If the caller asks about something you don't know, say "Let me have someone from the team get back to you on that"
6. If the caller asks to speak to a person, says they have a complaint, mentions legal issues, or becomes abusive, respond with EXACTLY: [TRANSFER_TO_HUMAN]
7. If the caller wants to cancel, respond with EXACTLY: [CANCEL_VIEWING] after confirming
8. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
9. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
10. Keep responses under 3 sentences - people don't like long speeches on the phone
11. If you can't understand after 3 tries, offer to send an SMS booking link

AVAILABLE PROPERTIES (use these for enquiries):
- PROP-001: 2-bed apartment, 45 Deansgate, Manchester, M3 2AB - £220,000 - Service charge £1,800/yr - Available
- PROP-002: 3-bed house, 12 Victoria Road, Leeds, LS1 5AE - £285,000 - Council tax Band D - Available
- PROP-003: 1-bed studio, 88 King Street, London, EC2V 8QR - £350,000 - Service charge £2,400/yr - Available
- PROP-004: 4-bed detached, 5 Oak Lane, Birmingham, B15 2TT - £425,000 - Council tax Band E - Under Offer
- PROP-005: 2-bed flat, 23 Harbour View, Bristol, BS1 4RW - £195,000 - Service charge £1,200/yr - Available

When PROP-004 is asked about, let them know it's currently under offer but suggest similar alternatives.`;

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
      max_tokens: 200,
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
    // Extract name from conversation if available
    const conversation = session.messages
      .filter((m) => m.role !== "system")
      .map((m) => m.content)
      .join(" ");

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
});// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses Deepgram for speech-to-text, OpenAI for the AI brain,
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

// --- AI System Prompt (the agent's personality and rules) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate, a property investment company based in the UK.

YOUR ROLE:
- Answer inbound customer calls warmly and professionally
- Help callers with property enquiries (prices, details, availability)
- Book, reschedule, or cancel property viewings
- Qualify leads by collecting: name, phone number, email, budget range, property interest
- Escalate to a human agent when needed

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking

RULES:
1. At the start of every call, greet the caller and mention call recording
2. Collect the caller's name early in the conversation
3. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
4. Always read back booking details and ask for confirmation before finalising
5. If the caller asks about something you don't know, say "Let me have someone from the team get back to you on that"
6. If the caller asks to speak to a person, says they have a complaint, mentions legal issues, or becomes abusive, respond with EXACTLY: [TRANSFER_TO_HUMAN]
7. If the caller wants to cancel, respond with EXACTLY: [CANCEL_VIEWING] after confirming
8. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
9. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
10. Keep responses under 3 sentences - people don't like long speeches on the phone
11. If you can't understand after 3 tries, offer to send an SMS booking link

AVAILABLE PROPERTIES (use these for enquiries):
- PROP-001: 2-bed apartment, 45 Deansgate, Manchester, M3 2AB - £220,000 - Service charge £1,800/yr - Available
- PROP-002: 3-bed house, 12 Victoria Road, Leeds, LS1 5AE - £285,000 - Council tax Band D - Available
- PROP-003: 1-bed studio, 88 King Street, London, EC2V 8QR - £350,000 - Service charge £2,400/yr - Available
- PROP-004: 4-bed detached, 5 Oak Lane, Birmingham, B15 2TT - £425,000 - Council tax Band E - Under Offer
- PROP-005: 2-bed flat, 23 Harbour View, Bristol, BS1 4RW - £195,000 - Service charge £1,200/yr - Available

When PROP-004 is asked about, let them know it's currently under offer but suggest similar alternatives.`;

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
      max_tokens: 200,
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
    // Extract name from conversation if available
    const conversation = session.messages
      .filter((m) => m.role !== "system")
      .map((m) => m.content)
      .join(" ");

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
});// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses Deepgram for speech-to-text, OpenAI for the AI brain,
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

// --- AI System Prompt (the agent's personality and rules) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate, a property investment company based in the UK.

YOUR ROLE:
- Answer inbound customer calls warmly and professionally
- Help callers with property enquiries (prices, details, availability)
- Book, reschedule, or cancel property viewings
- Qualify leads by collecting: name, phone number, email, budget range, property interest
- Escalate to a human agent when needed

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking

RULES:
1. At the start of every call, greet the caller and mention call recording
2. Collect the caller's name early in the conversation
3. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
4. Always read back booking details and ask for confirmation before finalising
5. If the caller asks about something you don't know, say "Let me have someone from the team get back to you on that"
6. If the caller asks to speak to a person, says they have a complaint, mentions legal issues, or becomes abusive, respond with EXACTLY: [TRANSFER_TO_HUMAN]
7. If the caller wants to cancel, respond with EXACTLY: [CANCEL_VIEWING] after confirming
8. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
9. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
10. Keep responses under 3 sentences - people don't like long speeches on the phone
11. If you can't understand after 3 tries, offer to send an SMS booking link

AVAILABLE PROPERTIES (use these for enquiries):
- PROP-001: 2-bed apartment, 45 Deansgate, Manchester, M3 2AB - £220,000 - Service charge £1,800/yr - Available
- PROP-002: 3-bed house, 12 Victoria Road, Leeds, LS1 5AE - £285,000 - Council tax Band D - Available
- PROP-003: 1-bed studio, 88 King Street, London, EC2V 8QR - £350,000 - Service charge £2,400/yr - Available
- PROP-004: 4-bed detached, 5 Oak Lane, Birmingham, B15 2TT - £425,000 - Council tax Band E - Under Offer
- PROP-005: 2-bed flat, 23 Harbour View, Bristol, BS1 4RW - £195,000 - Service charge £1,200/yr - Available

When PROP-004 is asked about, let them know it's currently under offer but suggest similar alternatives.`;

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
      max_tokens: 200,
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
    // Extract name from conversation if available
    const conversation = session.messages
      .filter((m) => m.role !== "system")
      .map((m) => m.content)
      .join(" ");

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
});// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses Deepgram for speech-to-text, OpenAI for the AI brain,
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

// --- AI System Prompt (the agent's personality and rules) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate, a property investment company based in the UK.

YOUR ROLE:
- Answer inbound customer calls warmly and professionally
- Help callers with property enquiries (prices, details, availability)
- Book, reschedule, or cancel property viewings
- Qualify leads by collecting: name, phone number, email, budget range, property interest
- Escalate to a human agent when needed

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking

RULES:
1. At the start of every call, greet the caller and mention call recording
2. Collect the caller's name early in the conversation
3. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
4. Always read back booking details and ask for confirmation before finalising
5. If the caller asks about something you don't know, say "Let me have someone from the team get back to you on that"
6. If the caller asks to speak to a person, says they have a complaint, mentions legal issues, or becomes abusive, respond with EXACTLY: [TRANSFER_TO_HUMAN]
7. If the caller wants to cancel, respond with EXACTLY: [CANCEL_VIEWING] after confirming
8. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
9. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
10. Keep responses under 3 sentences - people don't like long speeches on the phone
11. If you can't understand after 3 tries, offer to send an SMS booking link

AVAILABLE PROPERTIES (use these for enquiries):
- PROP-001: 2-bed apartment, 45 Deansgate, Manchester, M3 2AB - £220,000 - Service charge £1,800/yr - Available
- PROP-002: 3-bed house, 12 Victoria Road, Leeds, LS1 5AE - £285,000 - Council tax Band D - Available
- PROP-003: 1-bed studio, 88 King Street, London, EC2V 8QR - £350,000 - Service charge £2,400/yr - Available
- PROP-004: 4-bed detached, 5 Oak Lane, Birmingham, B15 2TT - £425,000 - Council tax Band E - Under Offer
- PROP-005: 2-bed flat, 23 Harbour View, Bristol, BS1 4RW - £195,000 - Service charge £1,200/yr - Available

When PROP-004 is asked about, let them know it's currently under offer but suggest similar alternatives.`;

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
      max_tokens: 200,
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
    // Extract name from conversation if available
    const conversation = session.messages
      .filter((m) => m.role !== "system")
      .map((m) => m.content)
      .join(" ");

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
});// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses Deepgram for speech-to-text, OpenAI for the AI brain,
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

// --- AI System Prompt (the agent's personality and rules) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate, a property investment company based in the UK.

YOUR ROLE:
- Answer inbound customer calls warmly and professionally
- Help callers with property enquiries (prices, details, availability)
- Book, reschedule, or cancel property viewings
- Qualify leads by collecting: name, phone number, email, budget range, property interest
- Escalate to a human agent when needed

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking

RULES:
1. At the start of every call, greet the caller and mention call recording
2. Collect the caller's name early in the conversation
3. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
4. Always read back booking details and ask for confirmation before finalising
5. If the caller asks about something you don't know, say "Let me have someone from the team get back to you on that"
6. If the caller asks to speak to a person, says they have a complaint, mentions legal issues, or becomes abusive, respond with EXACTLY: [TRANSFER_TO_HUMAN]
7. If the caller wants to cancel, respond with EXACTLY: [CANCEL_VIEWING] after confirming
8. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
9. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
10. Keep responses under 3 sentences - people don't like long speeches on the phone
11. If you can't understand after 3 tries, offer to send an SMS booking link

AVAILABLE PROPERTIES (use these for enquiries):
- PROP-001: 2-bed apartment, 45 Deansgate, Manchester, M3 2AB - £220,000 - Service charge £1,800/yr - Available
- PROP-002: 3-bed house, 12 Victoria Road, Leeds, LS1 5AE - £285,000 - Council tax Band D - Available
- PROP-003: 1-bed studio, 88 King Street, London, EC2V 8QR - £350,000 - Service charge £2,400/yr - Available
- PROP-004: 4-bed detached, 5 Oak Lane, Birmingham, B15 2TT - £425,000 - Council tax Band E - Under Offer
- PROP-005: 2-bed flat, 23 Harbour View, Bristol, BS1 4RW - £195,000 - Service charge £1,200/yr - Available

When PROP-004 is asked about, let them know it's currently under offer but suggest similar alternatives.`;

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
      max_tokens: 200,
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
    // Extract name from conversation if available
    const conversation = session.messages
      .filter((m) => m.role !== "system")
      .map((m) => m.content)
      .join(" ");

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
});// ============================================
// GFL REAL ESTATE - AI PHONE AGENT SERVER
// ============================================
// This server answers inbound phone calls via Twilio,
// uses Deepgram for speech-to-text, OpenAI for the AI brain,
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

// --- AI System Prompt (the agent's personality and rules) ---
const SYSTEM_PROMPT = `You are Alex, a friendly and professional AI phone assistant for GFL Real Estate, a property investment company based in the UK.

YOUR ROLE:
- Answer inbound customer calls warmly and professionally
- Help callers with property enquiries (prices, details, availability)
- Book, reschedule, or cancel property viewings
- Qualify leads by collecting: name, phone number, email, budget range, property interest
- Escalate to a human agent when needed

YOUR PERSONALITY:
- Friendly, calm, professional British tone
- Speak in short, clear sentences (this is a phone call, not an essay)
- Ask ONE question at a time
- Always confirm details before booking

RULES:
1. At the start of every call, greet the caller and mention call recording
2. Collect the caller's name early in the conversation
3. If a caller wants to book a viewing, collect: full name, phone number, preferred date, preferred time (morning/afternoon/evening)
4. Always read back booking details and ask for confirmation before finalising
5. If the caller asks about something you don't know, say "Let me have someone from the team get back to you on that"
6. If the caller asks to speak to a person, says they have a complaint, mentions legal issues, or becomes abusive, respond with EXACTLY: [TRANSFER_TO_HUMAN]
7. If the caller wants to cancel, respond with EXACTLY: [CANCEL_VIEWING] after confirming
8. If the caller wants to reschedule, respond with EXACTLY: [RESCHEDULE_VIEWING] after getting new date/time
9. When a booking is confirmed, respond with EXACTLY: [BOOK_VIEWING] followed by the details
10. Keep responses under 3 sentences - people don't like long speeches on the phone
11. If you can't understand after 3 tries, offer to send an SMS booking link

AVAILABLE PROPERTIES (use these for enquiries):
- PROP-001: 2-bed apartment, 45 Deansgate, Manchester, M3 2AB - £220,000 - Service charge £1,800/yr - Available
- PROP-002: 3-bed house, 12 Victoria Road, Leeds, LS1 5AE - £285,000 - Council tax Band D - Available
- PROP-003: 1-bed studio, 88 King Street, London, EC2V 8QR - £350,000 - Service charge £2,400/yr - Available
- PROP-004: 4-bed detached, 5 Oak Lane, Birmingham, B15 2TT - £425,000 - Council tax Band E - Under Offer
- PROP-005: 2-bed flat, 23 Harbour View, Bristol, BS1 4RW - £195,000 - Service charge £1,200/yr - Available

When PROP-004 is asked about, let them know it's currently under offer but suggest similar alternatives.`;

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
      max_tokens: 200,
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
    // Extract name from conversation if available
    const conversation = session.messages
      .filter((m) => m.role !== "system")
      .map((m) => m.content)
      .join(" ");

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
