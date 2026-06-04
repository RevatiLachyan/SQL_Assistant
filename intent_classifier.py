import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
 
INTENT_TO_CHART = {
    "trend":       "line",
    "ranking":     "bar_horizontal",
    "comparison":  "bar_grouped",
    "aggregation": "bar",
    "lookup":      "table",
}

VALID_INTENTS = set(INTENT_TO_CHART.keys())

CLASSIFIER_SYSTEM_PROMPT = """
You are a question intent classifier for a property management analytics app.
 
Your ONLY job is to read the user's question and return exactly ONE word
from this list:
 
  trend
  ranking
  comparison
  aggregation
  lookup
 
Definitions and examples:
 
- trend : question asks about change over time, by month, or by year
                Examples: "late payment trend by month"
                          "how has vacancy changed over the past year"
                          "show revenue by month"
 
- ranking : question asks for top N, bottom N, highest, lowest, most, least
                Examples: "top 5 most expensive repairs"
                          "which property has the lowest collection rate"
                          "bottom 3 tenants by credit score"
 
- comparison : question compares two or more values side by side
                Examples: "compare collected vs billed revenue by property"
                          "which property performs better"
                          "show billed vs collected side by side"
 
- aggregation : question asks for a total, average, count, or sum
                with no time dimension and no top-N framing
                Examples: "how many tenants pay by ACH"
                          "what is the average credit score by property"
                          "total outstanding balance by tenant"
 
- lookup : question asks for specific records, individual tenant details,
                a particular lease, or a filtered list with no aggregation
                Examples: "which tenants have outstanding balances over $500"
                          "show leases expiring in the next 90 days"
                          "find tenant Harry Potter"
 
Rules:
- Return ONLY the single intent word. No punctuation. No explanation.
- If you are unsure, return: lookup
""".strip()


def classify_intent(question: str) -> dict:
     try:
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0,
            max_tokens=5,
            messages=[
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user",   "content": question},
            ],
        )
        raw = response.choices[0].message.content.strip().lower()
        if raw not in VALID_INTENTS:
            print(f"[intent_classifier] Unexpected response: '{raw}' — falling back to 'lookup'")
            intent = "lookup"
        else:
            intent = raw
        return {
            "intent":     intent,
            "chart_type": INTENT_TO_CHART[intent],
            "raw":        raw,
        }
     
     except Exception as e:
        print("API call failed")

        return {
            "intent":     "lookup",
            "chart_type": "table",
            "raw":        None,
        }
 
if __name__=="__main__":
    test_questions =[("What is the late payment trend by month?",             "trend"),
        ("Top 5 most expensive completed maintenance repairs",   "ranking"),
        ("Compare collected vs billed revenue by property",      "comparison"),
        ("How many tenants pay by ACH?",                         "aggregation"),
        ("Which tenants have outstanding balances over $500?",   "lookup")]
    passed = 0
    for question, expected in test_questions:
        result = classify_intent(question)
        got    = result["intent"]
        chart  = result["chart_type"]
        match="yes" if got==expected else "no"
        if got == expected:
            passed += 1
        print(f"Score: {passed}/{len(test_questions)} correct")
