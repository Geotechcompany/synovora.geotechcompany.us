# LinkedIn Post Generator & Publisher

An automated LinkedIn post generator and publisher system powered by AI (CrewAI/OpenAI) and LinkedIn's Share API. Generate engaging, high-IQ LinkedIn posts, review them, and publish directly to LinkedIn.

## 🚀 Features

- **AI-Powered Post Generation**: Uses CrewAI agents to create engaging, human-style LinkedIn posts
- **Profile-Aware Writing**: Automatically pulls your LinkedIn headline/bio to shape every draft
- **Live Trend Research**: Dedicated research agent scans the web for niche-relevant trending topics
- **Profile Analytics Panel**: Surfaces LinkedIn follower counts, connections, and workspace stats
- **LinkedIn Intelligence Agent**: CrewAI-powered analyst summarizing scraped profile data for better content cues
- **Post Management**: Save drafts, edit posts, and track publication status
- **Direct Publishing**: Publish posts directly to LinkedIn via the Share API
- **One-Click Emailing**: Ship drafts to your inbox or stakeholders over Gmail SMTP
- **Clean Dashboard**: Beautiful, modern UI built with Tailwind CSS
- **Modular Architecture**: Easy to extend with additional features like scheduling
- **RESTful API**: Full FastAPI backend with comprehensive endpoints

## 📋 Requirements

- Python 3.8+
- Node.js 18+ (for the optional headless scraper)
- OpenAI/Gemini/NVIDIA API key
- LinkedIn OAuth 2.0 access token
- LinkedIn Profile URN
- Serper.dev API key (for internet trend research, optional but recommended)
- Gmail SMTP credentials (or any SMTP relay) for email sending

## 🛠️ Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd linkedin-automation
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your credentials
   ```

5. **Configure your `.env` file:**
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   LINKEDIN_TOKEN=your_linkedin_access_token_here
   PROFILE_URN=urn:li:person:your_profile_id_here
   ```

6. **Install Playwright browser binaries (once)**
   ```bash
   playwright install chromium
   ```

7. **(Optional) Build via Docker**
   ```bash
   docker build -t linkedin-backend .
   docker run --env-file .env -p 8000:8000 linkedin-backend
   ```

## 🔑 Getting LinkedIn Credentials

### Option 1: Using LinkedIn Developer Portal (Recommended)

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Create a new app
3. Request access to "Share on LinkedIn" product
4. Set up OAuth 2.0 redirect URLs
5. Generate an access token with `w_member_social` scope
6. Get your Profile URN from the API or your profile URL

### Option 2: Manual Token Generation

1. Use LinkedIn's OAuth 2.0 flow to get an access token
2. The token should have `w_member_social` permission
3. Find your Profile URN (format: `urn:li:person:abc123xyz`)

**Note**: Access tokens expire. You'll need to refresh them periodically or implement token refresh logic.

## 🚀 Running the Application

### Start the server:
```bash
python app.py
```

Or using uvicorn directly:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Access the dashboard:
Open your browser and navigate to:
```
http://localhost:8000
```

## 📡 API Endpoints

### Generate Post
```http
POST /generate
Content-Type: application/json

{
  "topic": "The future of remote work",
  "additional_context": "Focus on team collaboration"
}
```

### Publish Post
```http
POST /publish
Content-Type: application/json

{
  "post_id": 1,
  "visibility": "PUBLIC"
}
```

### List Posts
```http
GET /posts
GET /posts?status=draft
GET /posts?status=published
```

### Get Post
```http
GET /posts/{post_id}
```

### Update Post
```http
PUT /posts/{post_id}
Content-Type: application/json

{
  "content": "Updated post content",
  "status": "draft"
}
```

### Delete Post
```http
DELETE /posts/{post_id}
```

### Email Post
```http
POST /posts/{post_id}/email
Content-Type: application/json

{
  "recipients": ["you@example.com"],
  "subject": "LinkedIn Draft: Topic",
  "intro": "Optional intro line",
  "include_image": true
}
```

### Profile Insights
```http
GET /profile/insights
```
Returns LinkedIn profile metadata, follower/connection counts, workspace content stats, and CrewAI-generated insights. When `LINKEDIN_SCRAPER_LI_AT` is configured, the Python Playwright scraper runs once to enrich metrics and bio data before summarizing.

## ☁️ Deploying on Render (Docker)

1. Push this repository (with `render.yaml`) to GitHub.
2. In Render, create a new Blueprint deployment pointing at the repo.
3. Define required environment variables in the Render dashboard (`PORT`, `MONGODB_URI`, `LINKEDIN_TOKEN`, `PROFILE_URN`, AI keys, `LINKEDIN_SCRAPER_LI_AT`, SMTP creds, etc.).
4. Render will build using `backend/Dockerfile` and expose the service at `https://your-service.onrender.com`.

The Dockerfile installs Playwright + Chromium and runs `uvicorn`. Update Render env vars whenever tokens change.

### Check Auth Status
```http
GET /auth/status
```

### Get OAuth URL
```http
GET /auth/url
```

## 🏗️ Project Structure

```
linkedin-automation/
├── app.py                      # FastAPI main application
├── agents/
│   └── linkedin_post_agent.py  # CrewAI agent for post generation
├── utils/
│   ├── linkedin_api.py         # LinkedIn API integration
│   └── database.py             # JSON-based post storage
├── templates/
│   └── dashboard.html          # Web dashboard UI
├── posts.json                  # Database file (auto-created)
├── .env                        # Environment variables (create from .env.example)
├── .env.example                # Example environment file
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🧠 How It Works

1. **Post Generation**: 
   - User provides a topic
   - CrewAI agents (Content Creator + Editor) generate a high-quality post
   - Post follows LinkedIn best practices (hook, insight, question, <150 words)

2. **Post Management**:
   - Generated posts are saved as drafts
   - Users can edit, save, or delete posts
   - Posts are stored in `posts.json` (can be migrated to SQLite/PostgreSQL)

3. **Publishing**:
   - User reviews and approves a post
   - System publishes to LinkedIn via Share API
   - Post status is updated to "published"

## 🔧 Configuration

### Post Generation Rules

The system uses this prompt template:
> "Write a high-IQ, human-style LinkedIn post about {TOPIC}. Keep it under 150 words, with a hook in the first two lines, a genuine insight, and a question at the end. Use emojis naturally, avoid jargon, and sound personal yet smart."

### Customization

- **Modify generation prompt**: Edit `agents/linkedin_post_agent.py`
- **Change database**: Replace `utils/database.py` with SQLite/PostgreSQL
- **Add scheduling**: Extend `app.py` with scheduling logic
- **Customize UI**: Edit `templates/dashboard.html`
- **Disable trend research**: Skip configuring `SERPER_API_KEY` (the system will fall back to topic-only generation)
- **Enable headless profile scraping**: Set `LINKEDIN_SCRAPER_LI_AT` (li_at cookie) and optionally `LINKEDIN_SCRAPER_PROFILE_URL`. The built-in Playwright scraper plus the CrewAI “LinkedIn Intelligence Analyst” agent will automatically summarize the scraped data for the dashboard.
- **Switch email provider**: Update `SMTP_*` vars in `.env` to match your relay (Gmail, SES, Mailgun, etc.)

## 🧪 Testing

### Test the agent directly:
```bash
python agents/linkedin_post_agent.py
```

### Test LinkedIn API:
```bash
python utils/linkedin_api.py
```

### Test database:
```bash
python utils/database.py
```

## 📝 Example Usage

### Generate a post:
```python
from agents.linkedin_post_agent import generate_linkedin_post

post = generate_linkedin_post("The future of AI in healthcare")
print(post)
```

### Publish a post:
```python
from utils.linkedin_api import LinkedInAPI

api = LinkedInAPI()
result = api.post_text_content("Your post content here")
print(result)
```

## 🔒 Security Notes

- **Never commit `.env` file** - it contains sensitive credentials
- **Use environment variables** for all secrets
- **Rotate tokens regularly** - LinkedIn tokens expire
- **Limit API access** in production (use proper authentication)

## 🚧 Future Enhancements

- [ ] Post scheduling functionality
- [ ] Multiple LinkedIn account support
- [ ] Analytics and engagement tracking
- [ ] A/B testing for posts
- [ ] Content calendar view
- [ ] SQLite/PostgreSQL database support
- [ ] Token refresh automation
- [ ] Image/media support for posts
- [ ] Integration with CrewAI workflows

## 🐛 Troubleshooting

### "OPENAI_API_KEY not set"
- Make sure your `.env` file exists and contains `OPENAI_API_KEY`

### "LinkedIn token is invalid"
- Your token may have expired. Generate a new one from LinkedIn Developer Portal
- Check that your token has `w_member_social` scope

### "Profile URN not found"
- Get your URN from LinkedIn API: `GET https://api.linkedin.com/v2/me`
- Or extract it from your profile URL

### Posts not generating
- Check OpenAI API key is valid
- Ensure you have API credits
- Check console for error messages

## 📄 License

This project is provided as-is for educational and development purposes.

## 🤝 Contributing

Feel free to extend this project with:
- Additional CrewAI agents
- Enhanced UI features
- Database migrations
- Scheduling capabilities
- Analytics integration

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review LinkedIn API documentation
3. Check CrewAI documentation
4. Review FastAPI documentation

---

**Built with**: FastAPI, CrewAI, OpenAI, LinkedIn API, Tailwind CSS




