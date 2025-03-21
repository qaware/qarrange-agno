# QArrange (implementation using Agno)

This repository contains an AI-agent-based tool assisting in scheduling meetings. It makes use of the AI agent 
framework [Agno](https://github.com/agno-agi/agno) which is configured via Python.

## Goal

The goal is to assist users with finding time slots for meetings given the following constraints:
- Each user has a calendar with several blockers of varying importance.
- Each user has personal preferences regarding working hours, importance of specific meetings, etc.

## Features

- The scheduling can be initiated directly via Slack (realized via [slack-sdk](https://pypi.org/project/slack-sdk) and [slack-bolt](https://pypi.org/project/slack-bolt) using socket mode for now).
- The personal preferences can be stored via the app's home page in Slack and are be written to a SQlite database.
- QArrange stores user sessions in a SQlite database.
- QArrange has access to calendars (not yet implemented, currently mocked).
- QArrange can create calendar events after successful scheduling (not yet implemented).
- QArrange uses OpenAI language models for its agents.

## Agent architecture

- The initiating user queries **Secretary Agent** via Slack, providing information about the meeting (title, roughly the desired day or week, duration, participants).
- **Secretary Agent** makes sure that all information is gathered and asks for confirmation before proceeding. It then queries **Broker Agent** with the collected information.
- **Broker Agent** requests available time slots from the individual **User Agents** and negotiates back and forth in case of conflicts, aiming for consensus.
- **User Agents** (one per meeting participants, including the initiator) have access to the personal calendars and preferences and represent their users in the negotiation.

## Possible next steps

- Calendar integration (currently mocked)
- Slack integration for feedback to the participants after successful scheduling
- Facilitate deployment to a cloud via proper Docker setup
- Proper structuring of the Python project
