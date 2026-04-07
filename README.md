# Sales-AI CRM & Admin Portal

Internal administrative portal for managing supplements inventory, customers, prescriptions, subscriptions, and orders. The system features a modern, responsive UI and integrates a natively integrated Google GenAI agent module for automated customer communication on WhatsApp.

## 🚀 Features

- **Product & Inventory Management**: 
  - Administer Supplements catalog.
  - Stock tracking globally.
  - **Dynamic Product Fields (JSON)**: Create completely custom schema-less attributes (e.g., Size, Flavor, Color) managed entirely from the UI, making the catalog adaptable to any e-commerce vertical.
- **Customer & Subscription CRM** (Toggleable feature):
  - Manage customers, their objective profiles, and medical notes.
  - Full subscription engine allowing creation of automated fulfillment schedules.
  - Order history tracking and active lifecycle overview per customer.
- **Order Management (POS)**: 
  - Create orders, calculate cart prices manually.
- **AI Automation Integration (Agentic Google GenAI)**: 
  - Native Python-powered backend allowing direct Google GenAI bindings to read SQL DB and auto-reply to users seamlessly.
  - Dedicated Administration Prompt and UI Panel integrated to manage memory logic seamlessly.
- **System Configuration (SaaS Ready)**:
  - Global UI Dashboard to manage App toggles (Subscriptions, Marketing) via Database instead of static `.env` flags.
  - Dynamically configure business identity traits directly from the UI (e.g. Master Theme Colors, Bank info, branches).
- **Role-Based Access Control**: 
  - Secure login with JWT Authentication.
  - Features two strict security tiers: **admin** (Superusers with config rights) and **seller** (Day-to-day sales agent).

## 🛠 Tech Stack

- **Backend**: Python 3.10+ with [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: PostgreSQL (Production) / SQLite (Dev) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async)
- **Frontend**: Server-Side Rendering with Jinja2 Templates + Vanilla JS
- **Styling**: Modern, Database-driven Theme UI (Configurable without touching code) + Vanilla JS.

## 📦 Setup & Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd sales-ai
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file based on `.env.example`.
   ```bash
   cp .env.example .env
   # Edit .env with your specific configuration
   ```

   **Database Options**:
   
   - **Option A: SQLite (Default / Local Dev)**
     ```bash
     DATABASE_URL="sqlite+aiosqlite:///./sales-ai.db"
     ```
   
   - **Option B: Managed Database (PostgreSQL - Production)**
     ```bash
     # Standard URL (The app will automatically map this to the asyncpg driver)
     DATABASE_URL="postgres://dbmasteruser:password@hostname:5432/dbmaster"
     ```

5. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

6. **Seed Initial Admin User (Optional but Recommended)**
   ```bash
   python3 scripts/seed_data.py
   ```

7. **Run Server**
   ```bash
   uvicorn app.main:app --reload
   ```

## 🚀 Deployment

For detailed deployment instructions on AWS Lightsail, please refer to [DEPLOYMENT.md](DEPLOYMENT.md).

## 📂 Project Structure

- `app/api`: API Routers and Endpoints.
- `app/core`: Configuration, Security, and Database connections.
- `app/models`: SQLAlchemy Database Models.
- `app/schemas`: Pydantic Schemas for data validation.
- `app/services`: Business logic layer.
- `app/templates`: Jinja2 Frontend Templates.
- `app/static`: Static Assets (CSS, JS, Images).
