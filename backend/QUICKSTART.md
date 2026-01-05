# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your credentials:
# - OPENAI_API_KEY (required)
# - LINKEDIN_TOKEN (required for publishing)
# - PROFILE_URN (required for publishing)
```

### Step 3: Run the Application
```bash
# Option 1: Using the run script (recommended)
python run.py

# Option 2: Direct uvicorn
uvicorn app:app --reload --port 8000
```

### Step 4: Open Dashboard
Navigate to: **http://localhost:8000**

## 📝 Basic Usage

1. **Generate a Post:**
   - Enter a topic in the dashboard
   - Click "Generate Post"
   - Review the AI-generated content

2. **Edit & Save:**
   - Click "Edit" to modify the post
   - Click "Save Draft" to store it

3. **Publish:**
   - Click "Publish to LinkedIn"
   - Confirm the action
   - Post will be published to your LinkedIn profile

## 🔑 Getting LinkedIn Credentials

### Quick Method (Using LinkedIn Developer Portal):

1. Visit: https://www.linkedin.com/developers/
2. Create a new app
3. Request "Share on LinkedIn" product access
4. Generate OAuth token with `w_member_social` scope
5. Get your Profile URN from API response

### Profile URN Format:
```
urn:li:person:abc123xyz
```

## 🧪 Test Components

### Test Post Generation:
```bash
python agents/linkedin_post_agent.py
```

### Test LinkedIn API:
```bash
python utils/linkedin_api.py
```

### Test Database:
```bash
python utils/database.py
```

## ⚠️ Common Issues

**"OPENAI_API_KEY not set"**
- Make sure `.env` file exists and contains your key

**"LinkedIn token invalid"**
- Token may have expired - generate a new one
- Ensure token has `w_member_social` permission

**"Profile URN not found"**
- Get it from: `GET https://api.linkedin.com/v2/me`
- Or check your LinkedIn Developer Portal

## 📚 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API endpoints at http://localhost:8000/docs
- Customize post generation in `agents/linkedin_post_agent.py`
- Add scheduling features (see README for ideas)

---

**Happy Posting! 🎉**




