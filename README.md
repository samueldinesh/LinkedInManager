# LinkedIn Content Agency

An automated social media agency for Quantum Computing content, running on Raspberry Pi.

## Features

- **Trend Discovery**: AI-powered search for latest Quantum Computing news, breakthroughs, and government schemes
- **Content Strategy**: Weekly planning with categorized posts (Lessons, Breakthroughs, Schemes)
- **Multi-Agent Writing**: Gemini-powered content generation, editing, and LinkedIn formatting
- **Web Dashboard**: FastAPI-based interface for monitoring and approval
- **LinkedIn Integration**: Automated posting with OAuth authentication
- **Rate Limiting**: Built-in throttling to respect API limits

## Setup

### Prerequisites
- Python 3.8+
- Raspberry Pi (recommended for 24/7 operation)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd linkedin-content-agency
```

2. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```bash
GEMINI_API_KEY=your_gemini_api_key
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
```

5. Initialize database:
```bash
python init_db.py
```

### LinkedIn Authentication

1. Run the dashboard:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. Visit `http://localhost:8000/linkedin/auth` to start OAuth flow
3. Complete LinkedIn authorization
4. Tokens will be saved to `.env`

## Usage

### Web Dashboard
- **Home**: Overview of trends, plans, and posts
- **Trends**: View discovered content opportunities
- **Plans**: Review weekly content strategies
- **Posts**: Approve and publish generated content

### Automated Workflow
Run the main orchestrator:
```bash
python main.py
```

This will:
1. Discover new trends
2. Create a weekly plan
3. Generate post content
4. Wait for manual approval

### Raspberry Pi Deployment

1. Install system dependencies:
```bash
sudo apt update
sudo apt install python3 python3-pip
```

2. Set up as systemd service:
```bash
sudo cp deployment/linkedin-agency.service /etc/systemd/system/
sudo systemctl enable linkedin-agency
sudo systemctl start linkedin-agency
```

3. Set up cron for weekly runs:
```bash
crontab -e
# Add: 0 9 * * 1 /path/to/project/venv/bin/python /path/to/project/main.py
```

## Architecture

- **Agents**: Specialized Gemini-powered agents for different tasks
- **Database**: SQLite for persistence
- **Rate Limiter**: Token bucket algorithm for API throttling
- **Web Framework**: FastAPI with Jinja2 templates

## API Limits

- Gemini: 15 requests/minute
- LinkedIn: Respect posting frequency guidelines

## Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation

## License

MIT License