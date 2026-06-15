# 🚀 ShortlistAI Full Setup & Restore Guide

Follow these steps to set up the backend, frontend, and database on your local machine.

---

## 1. Database Setup (PostgreSQL)

Make sure you have **PostgreSQL** installed and running on your machine.

### Step 1.1: Create the Database
Create a database named `candidate_ai`. You can do this in pgAdmin, or run the following command in your terminal:
```sql
CREATE DATABASE candidate_ai;
```

### Step 1.2: Import Database Snapshot
Navigate to the root of the unzipped project directory in your terminal and run:
```bash
psql -U postgres -d candidate_ai -f candidate_ai_backup.sql
```
*(Enter your local PostgreSQL `postgres` user password when prompted. This will automatically import all custom candidates, recruiters, and logs).*

### Step 1.3: Configure environment variables
Verify database connection details in **`Backend/.env`**:
```env
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/candidate_ai
```

---

## 2. Backend Setup (Flask & Python)

From the root directory of the project, run:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the Backend Server
python Backend/run.py
```
*Note: The backend will start on port `5001` (http://localhost:5001).*

---

## 3. Frontend Setup (React & Vite)

Open a new terminal window, navigate to the frontend directory, and run:

```bash
# Navigate to frontend folder
cd frontend

# Install Node modules
npm install

# Start the Frontend Server
npm run dev
```
*Note: The frontend will start on port `8081` (http://localhost:8081).*

---

## 4. Test Accounts & Login Credentials

Here is a list of all user accounts already set up in this database:

| Role | Email | Password |
|---|---|---|
| **Superadmin** | `admin@test.com` | `123456789` |
| **Superadmin** | `admin@shortlist.ai` | `Admin123` |
| **Recruiter 1** | `recruiter1@test.com` | `123456789` |
| **Recruiter 2** | `recruiter2@test.com` | `123456789` |
| **Candidate 1** | `candidate1@test.com` | `123456789` |
| **Candidate 2** | `candidate2@test.com` | `123456789` |
| **Candidate 3** | `candidate3@test.com` | `123456789` |
| **Candidate 4** | `candidate4@test.com` | `123456789` |
| **Candidate 5** | `candidate5@test.com` | `123456789` |
| **Candidate 6** | `candidate6@test.com` | `123456789` |
