# FastForward TM - PDF Document Organizer

Automatically splits PDF packets, organizes documents in your preferred order, and extracts key transaction data using AI.

## Quick Start (Local Testing - This Weekend)

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Locally
```bash
python app.py
```
- Opens at: `http://localhost:5000`
- Upload your PDF packet
- Enter your OpenAI API key
- Get back organized PDFs + extracted data

### 3. Test with Sample PDFs
Use the three test PDFs provided to verify extraction works correctly.

---

## Deployment to Render (Monday Morning)

### Step 1: Push Code to GitHub
1. Create a GitHub account (if you don't have one)
2. Create a new repository: `fastforward-pdf-organizer`
3. Push this code:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/fastforward-pdf-organizer
   git push -u origin main
   ```

### Step 2: Deploy to Render
1. Go to https://render.com
2. Sign up (free)
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Fill in:
   - **Name**: `fastforward-pdf-app`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. Add Environment Variable:
   - **Key**: `OPENAI_API_KEY`
   - **Value**: Your OpenAI API key
7. Click "Deploy" (takes 2-3 minutes)

### Step 3: Connect Subdomain to Your Domain
1. After Render deployment, you'll get a URL like: `fastforward-pdf-app.onrender.com`
2. Go to Google Domains
3. Navigate to DNS settings for `fastforwardtm.com`
4. Add CNAME record:
   - **Name**: `fileinput`
   - **Type**: CNAME
   - **Data**: `fastforward-pdf-app.onrender.com`
5. Wait 5-10 minutes for DNS to propagate

### Step 4: Access Your App
- Your team accesses: **https://fileinput.fastforwardtm.com**

---

## Document Organization Order

PDFs are automatically sorted in this order:
1. Pre-Approval Letter / Proof of Funds
2. Agency Disclosure
3. Team Disclosure
4. Purchase Agreement
5. Addendums
6. Property Disclosure
7. Lead Paint Disclosure
8. Affiliated Business Arrangement (ABA)
9. Other documents

---

## Features

✅ Splits multi-page PDF packets into individual documents  
✅ Auto-classifies documents  
✅ Organizes in your preferred order  
✅ Extracts transaction data:
  - Dates (effective, earnest money due, loan deadline, inspection, ROC, closing, possession)
  - Parties (buyers, sellers, agents, title company, lender)
  - Property details (address, price)
  - Additional terms & conditions

✅ Downloads organized PDFs as ZIP  
✅ No data stored - files processed in memory  
✅ Team members use via web browser  

---

## Troubleshooting

**"API key invalid"**
- Check your OpenAI API key is correct
- Regenerate it at https://console.openai.com/account/keys

**Deployment won't start**
- Check Render logs (Dashboard → Service → Logs tab)
- Common: Missing environment variable

**Subdomain not working**
- DNS takes 5-30 minutes to propagate
- Verify CNAME record in Google Domains

---

## Support

All files process locally. No data leaves your instance.

For questions, check Render's documentation or OpenAI's API docs.

---

## Costs

- **Render**: Free tier (may be slow on free tier; upgrade to paid if needed)
- **OpenAI API**: $0.003 per 1K input tokens, $0.015 per 1K output tokens
  - Typical transaction: ~$0.10-0.20 per file
  - 150-200 files/month = ~$20-30/month
