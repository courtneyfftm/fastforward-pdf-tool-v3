# Deployment Checklist - Monday Morning

## Pre-Deployment (Do Saturday/Sunday)

- [ ] Download all files from Claude
- [ ] Create GitHub account (5 min)
- [ ] Create Render account (5 min)

---

## Monday Morning - Go Live (30 minutes)

### 1. Push to GitHub (5 min)
```bash
# In the app folder:
git init
git add .
git commit -m "Initial commit - FastForward PDF organizer"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fastforward-pdf-organizer
git push -u origin main
```

### 2. Deploy to Render (10 min)
1. Log in to render.com
2. Click "New +" → "Web Service"
3. Connect GitHub (authorize Render)
4. Select your `fastforward-pdf-organizer` repo
5. Fill in settings:
   - **Name**: `fastforward-pdf-app`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. **Environment Variables** → Add:
   - **Key**: `OPENAI_API_KEY`
   - **Value**: `sk-ant-usr-...` (paste your API key)
7. Click **Deploy**
8. Wait for build (2-3 min) - status shows "Live" when done
9. Copy the Render URL (looks like: `fastforward-pdf-app.onrender.com`)

### 3. Add Subdomain (10 min)
1. Go to Google Domains
2. Find your DNS settings for `fastforwardtm.com`
3. Find or create CNAME records section
4. Add new record:
   - **Subdomain**: `fileinput`
   - **Type**: CNAME
   - **TTL**: 3600 (or default)
   - **Data/Value**: `fastforward-pdf-app.onrender.com`
5. Save
6. **Wait 5-15 minutes** for DNS to propagate

### 4. Test (5 min)
1. Go to: `https://fileinput.fastforwardtm.com`
2. Should see the purple form
3. Test with your sample PDFs:
   - Use the app; the API key is securely configured on the server
   - Upload Test_1.pdf (or Test_2.pdf)
   - Click "Process PDF"
   - Should download organized PDFs in 30-60 sec

### 5. Share with Team
- Send them: **https://fileinput.fastforwardtm.com**
- Share TEAM_SETUP.md (simple instructions)
- Tell them to use the shared API key (or give each person their own if preferred)

---

## Verify Everything Works

✅ Website loads cleanly  
✅ Can upload PDFs  
✅ Gets organized PDFs back  
✅ PDFs are in your preferred order  
✅ Team can access from their computers  

---

## If Something Goes Wrong

**Render shows build error**
- Check "Deploy logs" tab
- Usually: missing requirements.txt or typo in Python code
- Screenshot and send to Claude

**Subdomain not working after 15 min**
- Verify CNAME record in Google Domains
- Try clearing browser cache
- Try in incognito window

**Processing hangs or fails**
- Check Render "Logs" tab for errors
- Make sure API key is valid and has quota
- Try with smaller PDF (less pages)

---

## What Your Team Gets

- One web address: `fileinput.fastforwardtm.com`
- Upload messy PDF packet
- Download organized PDFs (sorted perfectly)
- Extracted data (bonus)
- No training needed - they'll figure it out

---

## Costs After Launch

**Render**: 
- Free tier ($0/mo) = slower, may go to sleep between uses
- Starter tier ($7/mo) = always responsive
- Upgrade if team complains it's slow

**OpenAI API**: 
- ~$0.10-0.25 per transaction (150-200 files = $20-30/mo)
- Monitor usage at: https://console.openai.com/account/keys

---

## You're Done

Once "Live" shows in Render and subdomain works, your team can start using it Monday afternoon.

Bookmark this: **https://fileinput.fastforwardtm.com**


## OpenAI configuration

In Render → Environment, add:
- `OPENAI_API_KEY` = your OpenAI API key
- `OPENAI_MODEL` = `gpt-6-astra` (optional; this is the default)

Keep the API key in Render. Do not put it in the webpage, source code, or Git repository.
