> [!NOTE]  
> This project is for demonstration purposes only and not intended for production use.

# QArrange (Implemented with Agno)

This repository contains an AI-agent-based tool assisting in scheduling meetings. It makes use of the AI agent
framework [Agno](https://github.com/agno-agi/agno) via Python.

## Goal

The goal is to assist users with finding time slots for meetings given the following constraints:

- Each user has a calendar with several blockers of varying importance.
- Each user has personal preferences regarding working hours, importance of specific meetings, etc.

## Features

- QArrange is a Slack app, providing an app home tab and offering a chatbot.
- The chatbot can be tasked with the scheduling of calendar events with other participants.
- The chatbot memorizes personal calendar preferences of the user. These preferences can be viewed and managed on the
  Slack app home tab.
- QArrange has access to calendars and can create events after successful scheduling.

## Agent Flow

![agent-flow.svg](agent-flow.svg)

### Event Scheduling

- A user queries the **Secretary Agent** via Slack, providing information about the meeting (title, desired
  date and time, duration, participants).
- The **Secretary Agent** makes sure that all necessary information is provided and asks for confirmation before
  proceeding. It then queries the **Broker Agent**.
- The **Broker Agent** requests available time slots from the individual **User Agents** and negotiates back and forth
  in case of conflicts, aiming for consensus.
- The **User Agents** (one per meeting participants) have access to user preferences and personal calendars and
  represent their users during the negotiation.
- After a working time slot has been reported back to the Secretary Agent, it will create a calendar event.

### Preference Memorization

- A user tells the **Secretary Agent** about any kind of preference regarding their calendar.
- The **Secretary Agent** asks the **Memory Agent** to store the provided preference.
- The **Memory Agent** rephrases the preference and stores it in a database.

## Tech Stack

- [Agno](https://github.com/agno-agi/agno)
- [slack-sdk](https://pypi.org/project/slack-sdk)
- [slack-bolt](https://pypi.org/project/slack-bolt) (in socket mode)
- Google Calendar
- SQLite (session storage, long-term memory)
- OpenAI language models

## Example Screenshots

![screenshot-0.png](screenshot-0.png)

![screenshot-1.png](screenshot-1.png)

## Example Logs

```
⚡️ Bolt app is running!
[U000000000A] App home opened.
[U000000000A-1763462485679699] Received message.
[U000000000A-1763462485679699-SecretaryAgent] Initializing.
[U000000000A-1763462485679699] Responded to message.
[U000000000A-1763462485679699] Received message.
[U000000000A-1763462485679699-SecretaryAgent] Initializing.
[U000000000A-1763462485679699-SecretaryAgent] Initialize scheduling of event:
  Title: KI-Themen
  Date: kommenden Donnerstag
  Duration: 1 Stunde
  Participants: ['U000000000A', 'U000000000B', 'U000000000C']
[U000000000A-1763462485679699-UserAgent-U000000000A] Initializing.
[U000000000A-1763462485679699-UserAgent-U000000000B] Initializing.
[U000000000A-1763462485679699-UserAgent-U000000000C] Initializing.
[U000000000A-1763462485679699-BrokerAgent] Initializing.
[U000000000A-1763462485679699-BrokerAgent] Negotiating.
[U000000000A-1763462485679699-UserAgent-U000000000A] Fetching calendar at 2025-11-20.
[GoogleCalendar] Fetching blocker events at 2025-11-20 from calendar a@group.calendar.google.com.
[GoogleCalendar] Fetched 2 blocker events.
[U000000000A-1763462485679699-UserAgent-U000000000B] Fetching calendar at 2025-11-20.
[GoogleCalendar] Fetching blocker events at 2025-11-20 from calendar b@group.calendar.google.com.
[GoogleCalendar] Fetched 1 blocker events.
[U000000000A-1763462485679699-UserAgent-U000000000C] Fetching calendar at 2025-11-20.
[GoogleCalendar] Fetching blocker events at 2025-11-20 from calendar c@group.calendar.google.com.
[GoogleCalendar] Fetched 1 blocker events.
[U000000000A-1763462485679699-SecretaryAgent] Creating event.
[GoogleCalendar] Creating event in calendar a@group.calendar.google.com: {'summary': 'KI-Themen', 'description': 'Created by QArrange.', 'start': {'dateTime': '2025-11-20T13:00:00+01:00'}, 'end': {'dateTime': '2025-11-20T14:00:00+01:00'}}
[GoogleCalendar] Created event: https://www.google.com/calendar/event?eid=...
[U000000000A-1763462485679699] Responded to message.
```

## Local Execution

### First-time Setup

Make sure to have `python3.10` available, e.g., via `brew install python@3.10` on macOS. Using this version is a
workaround for an issue similar to [this](https://github.com/resemble-ai/resemble-enhance/issues/52).

```shell
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Environment

Prepare your environment in [.env](.env) based on [.env.example](.env.example).

Furthermore, store credentials for a Google Cloud service account in
[google-calendar-service-account.json.secret](./google-calendar-service-account.json.secret). The account must be
permitted to assume the role "Service Account Token Creator".

### Execution

```shell
python main.py
```

### Observability

Run the Agno Agent OS:

```shell
python agent_os.py
```

In another terminal, run the Agno Agent UI:

```shell
npx create-agent-ui@latest
npm --prefix agent-ui run dev
```

## References

### Agno

- https://docs.agno.com/introduction

### Slack

- https://api.slack.com/docs
- https://tools.slack.dev/bolt-python
- https://app.slack.com/block-kit-builder

### Google

- https://developers.google.com/workspace/calendar/api/v3/reference