##CodeSense360 — AI-Powered Engineering Analytics Platform

CodeSense360 is an end-to-end cloud analytics platform that transforms raw GitHub and CI/CD data into actionable AI insights.
It automatically ingests repository metrics, analyzes developer activity with AWS Athena, visualizes KPIs via Streamlit, and delivers weekly OpenAI-generated summaries directly to Microsoft Teams.

#Project Overview

This project demonstrates a serverless and cost-efficient observability system for software engineering teams.
It tracks commits, pull requests, and CI/CD runs, then applies AI summarization to highlight team performance trends, productivity shifts, and potential risks — all powered by the AWS Free Tier.

#Core Objectives

Build a fully automated DevOps analytics stack on AWS
Apply AI (OpenAI GPT-4) to generate natural-language insights
Integrate results directly into a dashboard (Streamlit) and Teams notifications
Operate 100% serverless — no EC2, no manual triggers

#Architecture
             ┌────────────────────────────┐
             │        GitHub Repo         │
             │ (Commits / PRs / Workflows)│
             └────────────┬───────────────┘
                          │
            GitHub Actions (Daily / Manual)
                          │
          ┌───────────────▼────────────────┐
          │        AWS Lambda (Ingest)     │
          │ Fetches GitHub data, stores in │
          │ S3: commits / PRs / CI/CD runs │
          └───────────────┬────────────────┘
                          │
                    AWS S3 (Data Lake)
                 github/, cicd/, processed/
                          │
          ┌───────────────▼────────────────┐
          │       AWS Athena (Analytics)   │
          │ SQL over S3 CSV datasets       │
          └───────────────┬────────────────┘
                          │
             Streamlit Dashboard (Visuals)
          │ KPI charts + AI Insight panel │
                          │
          ┌───────────────▼────────────────┐
          │      OpenAI GPT-4 (Insights)   │
          │ Summarizes trends weekly       │
          └───────────────┬────────────────┘
                          │
          Microsoft Teams (Webhook)
        Weekly Adaptive Card Summary

#Tech Stack

| Layer             | Technology              | Purpose                             |
| ----------------- | ----------------------- | ----------------------------------- |
| **Ingestion**     | AWS Lambda + GitHub API | Fetch commits, PRs, build runs      |
| **Storage**       | AWS S3                  | Central data lake for all metrics   |
| **Analytics**     | AWS Athena (Trino)      | SQL queries over processed data     |
| **Processing**    | Python (Pandas, NumPy)  | Data cleaning & KPI computation     |
| **Visualization** | Streamlit Cloud         | Interactive, live dashboard         |
| **AI Insights**   | OpenAI GPT-4 API        | Summarizes weekly developer metrics |
| **Automation**    | GitHub Actions          | CI/CD for Lambda & weekly runs      |
| **Collaboration** | Microsoft Teams         | Automated Adaptive Card reports     |


#Key Features

Serverless ingestion pipeline — GitHub → AWS Lambda → S3
Auto-generated AI reports via GPT-4 summarization
Athena analytics layer for SQL-based exploration
Streamlit dashboard with real-time KPI and weekly insights
Microsoft Teams integration with rich Adaptive Card formatting
Zero-maintenance automation — runs on a daily/weekly schedule

#Streamlit Dashboard

The dashboard provides:
📈 Commit and PR metrics (by author, trend, merge rates)
⚙️ CI/CD success rates and build health
🧠 GPT-4 AI Insights (auto-updated weekly from S3)
☁️ Deployed on Streamlit Cloud (no infra management)

#Teams Integration

Each Monday, an Adaptive Card is posted to your Teams channel:
🧠 CodeSense360 Weekly AI Insights
📅 Week of November 10, 2025
📈 Commits ↑ 18% | PR merges ↑ 12% | Build reliability stable
“Developer activity shows strong improvement, with reduced review cycles.”

#AWS Cost Optimization

All services use Free Tier:
Lambda (≤ 1M requests/month)
S3 (≤ 5GB storage)
Athena (query-based billing — negligible for small data)
Streamlit Cloud (free app tier)

#Folder Structure

codesense360/
├── src/
│   ├── ingest/
│   │   ├── github_ingest.py
│   │   ├── cicd_ingest.py
│   │   └── s3_uploader.py
│   ├── process/
│   │   ├── metrics_processor.py
│   │   └── cicd_metrics_processor.py
│
├── dashboard/
│   ├── app.py
│   ├── weekly_ai_insights.py
│   └── config.yaml
│
├── .github/workflows/
│   ├── lambda_deploy.yml
│   └── weekly_ai_insights.yml
│
├── lambda_handler.py
├── requirements.txt
└── README.md

#Impact & Talking Points for Interviews

#Problem Solved:
Engineering teams often lack centralized visibility into code velocity, PR review patterns, and CI/CD health. CodeSense360 solves this by combining automation, analytics, and AI insight generation.

#Key Differentiators:
Full cloud pipeline built from scratch using free-tier AWS
GPT-powered contextual summaries (not just metrics)
Live dashboard + auto Teams notification
Designed for scalability — plug in multiple repos later

#Interview Highlights:
“Used Lambda for stateless ingestion, S3 as a central data lake, Athena for schema-on-read analytics.”
“Automated weekly AI insights using OpenAI + GitHub Actions.”
“Integrated with Teams using Adaptive Cards for seamless visibility.”
“Fully serverless — zero DevOps maintenance required.”

#Future Enhancements

Multi-repo aggregation (organization-wide view)
Trend forecasting via time-series ML models
Cost & deployment analytics from AWS CloudWatch
Slack / Jira integration for richer developer telemetry
