# Who Gets The Last Seat?

## Multi-Model AI Admissions Simulation

An evidence-driven conversational admissions pipeline built for the **Who Gets The Last Seat?** hackathon challenge.

The scenario has six applicants competing for five bootcamp seats:

- 2 seats with guaranteed job placement
- 3 training-only seats
- 1 rejection

The system interviews each applicant through multiple conversational turns, challenges vague claims, accounts for new information revealed during an interview, and asks a final AI committee to make the allocation.

## Why This Project

Admissions decisions are easy to oversimplify when candidates have very different needs, strengths, and opportunities. This project demonstrates a more transparent approach: gather evidence through follow-up questions, score candidates on consistent criteria, and explain the trade-offs behind the final decision.

## Features

- Multi-turn interviews with targeted follow-up questions
- Direct probing of unverifiable or vague experience claims
- Mid-interview pivots when a candidate reveals important new information
- Candidate scoring across immediate need, community multiplier, and technical readiness
- Separate placement and training-only recommendations
- Comparative rejection reasoning from the final committee
- Multi-model routing across Groq and OpenAI-compatible models
- Background Flask execution with live browser status polling
- Downloadable JSON output containing all dossiers and the final verdict

## Applicant Model Routing

| Applicant     | Scenario                                              | Model                |
| ------------- | ----------------------------------------------------- | -------------------- |
| A1 Amina      | Single mother needing immediate income                | `groq/compound`      |
| A2 Kofi       | Gifted 17-year-old with an existing safety net        | `groq/compound-mini` |
| A3 Kwame      | Persistent self-studier after two previous rejections | `groq/compound`      |
| A4 Mr. Mensah | Pensioner planning a free youth workshop              | `groq/compound-mini` |
| A5 Yaw        | Applicant with vague informal experience claims       | `openai/gpt-oss-20b` |
| A6 Akua       | Influential referral who receives an external offer   | `groq/compound`      |

The final admissions committee uses `groq/compound` to compare the completed candidate dossiers.

## Tech Stack

- Python 3.10+
- Flask
- Groq Python SDK
- `python-dotenv`
- Vanilla HTML, CSS, and JavaScript

## Getting Started

### Prerequisites

- Python 3.10 or newer
- A Groq API key with access to the configured models

### Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### Run the app

```bash
python server.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser, then select **Run admissions simulation**.

On Windows, use `python` instead of `python3` and activate the environment with `.venv\\Scripts\\activate`.

## Output

After a completed run, the app writes `last_seat_results.json` in the project root. The web interface also provides a download link for that file.

The output contains:

- Candidate evaluation dossiers
- Scores and rationale for each candidate
- The model used for each applicant
- The final committee allocation and justification

## API Endpoints

| Method | Endpoint        | Purpose                                   |
| ------ | --------------- | ----------------------------------------- |
| `GET`  | `/`             | Serves the web interface                  |
| `POST` | `/api/run`      | Starts a new simulation in the background |
| `GET`  | `/api/status`   | Returns simulation status and progress    |
| `GET`  | `/api/results`  | Returns the completed result as JSON      |
| `GET`  | `/api/download` | Downloads `last_seat_results.json`        |

## Project Structure

```text
app.py                 AI interview and admissions pipeline
server.py              Flask server and API endpoints
requirements.txt       Python dependencies
last_seat_results.json Latest generated simulation output
templates/index.html   Web interface markup
static/app.js          Browser behavior and result rendering
static/style.css       Application styles
```

## Notes

- Each run makes multiple API calls and may take a few minutes depending on model availability and rate limits.
- The simulation is a hackathon demonstration, not a production admissions system.
- Do not commit `.env`, API keys, virtual environments, or generated output unless you intentionally want to share that output.
