# SQL_Assistant
SQL_Assistant for Property Management Data

Natural Language Analytics for Property Portfolios
The problem

Property managers and portfolio analysts ask the same handful of questions every week: which tenants are behind on rent, what's the vacancy rate this month, which leases are expiring soon, where is maintenance spend piling up. Getting those answers usually means opening a report in Yardi or AppFolio, exporting to Excel, or pinging whoever on the team knows SQL. That's a bottleneck, and it slows down decisions that should take seconds.

The solution

PropQuery lets anyone type a question in plain English, for example "which tenants have outstanding balances over $1000," and get back a table, a chart, and the exact SQL that produced the answer. No SQL knowledge required to ask the question, but the SQL is always visible, so anyone who does know SQL can check it.

Why the business logic matters

Generic text-to-SQL tools guess at what terms like "vacancy rate" or "delinquent tenant" mean, and that guessing is usually where these tools go wrong in a real property management context, because the definitions are specific to the industry and sometimes to the company. This project bakes a business glossary straight into the prompt: outstanding balance, effective rent vs market rent, delinquent tenant, collection rate, and more. The model applies the same definitions a property accountant would use, not a generic interpretation.

That glossary comes directly from three years writing SQL for residential portfolios at Yardi Systems. The definitions in this app are the ones a real property management team would use.

How it works
NL to SQL core (nl_to_sql.py) - GPT-4o turns the question into a single SQLite SELECT statement, using the schema, the business glossary, and ten worked examples as context. If the query fails to run, the error gets fed back to the model once for a self-correction attempt.
Intent classifier (intent_classifier.py) - a lightweight GPT-4o call labels the question as a lookup, aggregation, comparison, trend, or ranking, and that label picks the right chart type automatically.
SQLite runner (db_runner.py) - executes the SQL, times it, and returns a clean pandas DataFrame or a readable error, never a raw stack trace.
Streamlit UI (app.py) - a single page where you ask the question, see the intent badge, expand the generated SQL, and view the results as a table and a chart.
Guardrails

The model is never allowed to write DROP, DELETE, UPDATE, INSERT, or ALTER statements. Any query containing one of those keywords is rejected before it touches the database. SELECT * is blocked unless the query has a WHERE clause, so nobody can accidentally pull every row of every table. Every failure gets translated into a plain-English message in the UI instead of a stack trace.

Try it

Example questions the app handles well:

Which tenants have outstanding balances over $500?
Show vacancy rate by property
What is the late payment trend by month?
Top 5 most expensive maintenance repairs
Compare collected vs billed revenue by property
Which active leases expire in the next 90 days?
Tech stack

Python, OpenAI GPT-4o, SQLite, Streamlit, Plotly, pandas.

Setup
Clone this repo.
Create a virtual environment and activate it.
Install dependencies: pip install -r requirements.txt
Copy .env.example to .env and add your OpenAI API key.
Generate the database: python generate_data.py
Run the app: streamlit run app.py

The database isn't included in this repo. Step 5 builds prop_mgmt.db locally in a few seconds, using Faker with a fixed seed to create 8 properties, 120 units, 110 tenants, and their leases, payments, invoices, and maintenance history. Same dataset every time, so results are reproducible, and there's no real tenant data anywhere near this project since none of it exists until you generate it.

