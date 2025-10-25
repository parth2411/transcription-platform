# CORS 400 Bad Request Fix

## Problem
`OPTIONS /api/auth/login` returns `400 Bad Request`

## What I Fixed

### 1. Updated CORS Configuration in [backend/app/main.py](backend/app/main.py)

**Changes**:
- ✅ Added explicit origin list (localhost:3000, localhost:8080, 127.0.0.1:3000, etc.)
- ✅ Cannot use `allow_origins=["*"]` with `allow_credentials=True` (CORS spec restriction)
- ✅ Added all common HTTP methods including OPTIONS
- ✅ Set max_age for preflight caching

### 2. Updated [.env](.env) file

**Added**:
```env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
DATABASE_URL=postgresql://user:password@localhost:5432/transcription_db
REDIS_URL=redis://localhost:6379
GROQ_RATE_LIMIT_ENABLED=true
GROQ_RATE_LIMIT_RPM=25
GROQ_RATE_LIMIT_RPD=10000
DIARIZATION_ENABLED=false
```

---

## 🔥 IMPORTANT: Restart Your Backend!

The backend must be restarted for changes to take effect:

```bash
# Stop current server (Ctrl+C in the terminal running it)

# Then restart:
cd backend
source .venv/bin/activate  # or: . .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ✅ Verify It's Working

### 1. Check Server Startup
You should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Test OPTIONS Request
```bash
curl -X OPTIONS http://localhost:8000/api/auth/login \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -v
```

**Expected**: `200 OK` with CORS headers like:
```
< HTTP/1.1 200 OK
< access-control-allow-origin: http://localhost:3000
< access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
< access-control-allow-headers: *
< access-control-allow-credentials: true
```

### 3. Test Actual Login
From your frontend, try to login. It should now work!

---

## 🐛 Still Getting 400?

### Check These:

1. **Did you restart the backend?**
   - CORS changes only apply after restart
   - Stop with Ctrl+C and restart

2. **Check which port frontend is using**
   ```bash
   # If frontend is on a different port, add it to main.py:
   allow_origins=[
       "http://localhost:3000",
       "http://localhost:YOUR_PORT",  # Add your port here
       ...
   ]
   ```

3. **Check browser console for CORS errors**
   - Open DevTools (F12)
   - Look for red CORS error messages
   - Share the exact error message

4. **Clear browser cache**
   - Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   - Or open in incognito/private window

5. **Check if backend is actually running**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy","database":"connected","version":"1.0.0"}
   ```

6. **Verify frontend API URL**
   Check [frontend/.env.local](frontend/.env.local):
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

---

## 🔍 Debug Commands

### Check what's running on port 8000:
```bash
lsof -i :8000
# or
netstat -an | grep 8000
```

### Check backend logs:
The terminal running uvicorn shows all requests. Look for:
- `OPTIONS /api/auth/login` - Should be 200, not 400
- `POST /api/auth/login` - Your actual login request

### Test with curl:
```bash
# Test OPTIONS (preflight)
curl -X OPTIONS http://localhost:8000/api/auth/login \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Test actual login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{"email":"test@example.com","password":"testpass"}' \
  -v
```

---

## 📋 Quick Checklist

Before reporting the issue:

- [ ] Backend is restarted after changes
- [ ] Backend shows "Application startup complete"
- [ ] Frontend is running on http://localhost:3000
- [ ] `.env` file has `ALLOWED_ORIGINS` set
- [ ] Browser cache is cleared
- [ ] Tested in incognito/private window
- [ ] `curl` test for OPTIONS returns 200

---

## 🆘 Still Not Working?

Share these details:

1. **Exact error from backend logs**:
   ```
   The line that shows: OPTIONS /api/auth/login ...
   ```

2. **Browser console error** (F12 → Console tab):
   ```
   Copy the CORS error message
   ```

3. **Which port is your frontend on?**:
   ```
   Check the URL in browser: http://localhost:XXXX
   ```

4. **Output of health check**:
   ```bash
   curl http://localhost:8000/health
   ```

5. **Output of OPTIONS test**:
   ```bash
   curl -X OPTIONS http://localhost:8000/api/auth/login \
     -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -v 2>&1 | grep -E "(HTTP|access-control)"
   ```

---

## 💡 Common Mistakes

❌ **Forgot to restart backend** → Must restart after changes
❌ **Frontend on different port** → Add port to allow_origins
❌ **Old browser cache** → Hard refresh or incognito
❌ **Wrong Origin header** → Frontend must match allowed origins exactly
❌ **Proxy/firewall blocking** → Check if any proxy is in the way

---

## ✨ After It's Working

Once login works, you might want to:

1. **Secure the SECRET_KEY** in `.env`
2. **Set up your database** (PostgreSQL)
3. **Test file upload** feature
4. **Read** [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment

---

That's it! The CORS issue should be resolved. Just **restart the backend** and try again! 🚀
