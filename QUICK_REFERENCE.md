# Quick Reference Card

## 🚀 Start Here

### 1. Understand the Fix (5 min)
```
Read: README_EVALUATION_FIX.md
Then: FLOW_DIAGRAM.md
```

### 2. Test It (5 min)
```bash
cd Backend
python test_evaluation_flow.py
```

### 3. Deploy It
```
Follow: IMPLEMENTATION_SUMMARY.md → Deployment Checklist
```

---

## 📋 What Changed

| File | Change | Lines |
|------|--------|-------|
| Backend/agents/__init__.py | Task status tracking | +10 |
| Backend/api.py | Fixed recruiter action endpoint | +50 |
| frontend/src/pages/candidate/Applications.tsx | Improved polling | +150 |
| frontend/src/pages/recruiter/Candidates.tsx | Better action handling | +15 |

**Total:** ~225 lines of code

---

## 🔄 The Flow (30 seconds)

```
Candidate expresses interest
    ↓ (POST /jobs/{id}/express-interest)
Background evaluation starts
    ↓ (Groq LLM, 10-30 seconds)
Candidate polls every 2 seconds
    ↓ (GET /candidate/evaluations/{id})
Evaluation completes with score
    ↓
Recruiter shortlists/rejects
    ↓ (POST /recruiter/action)
Candidate polls every 5 seconds
    ↓ (GET /candidate/evaluations)
Candidate sees recruiter action
```

---

## 🧪 Testing

### Automated (2 min)
```bash
python Backend/test_evaluation_flow.py
```

### Manual (5 min)
1. Create recruiter account
2. Create candidate account
3. Recruiter posts job
4. Candidate expresses interest
5. Watch evaluation (10-30 seconds)
6. Recruiter shortlists
7. Candidate sees update (< 5 seconds)

### API (with cURL)
```bash
# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"candidate@test.com","password":"password123"}'

# Express interest
curl -X POST http://localhost:5000/api/jobs/1/express-interest \
  -H "Authorization: Bearer $TOKEN"

# Poll evaluation
curl -X GET http://localhost:5000/api/candidate/evaluations/1 \
  -H "Authorization: Bearer $TOKEN"

# Recruiter action
curl -X POST http://localhost:5000/api/recruiter/action \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"candidate_id":1,"job_id":1,"action":"shortlist"}'
```

---

## 📊 Performance

| Metric | Expected | Actual |
|--------|----------|--------|
| Evaluation time | 10-30s | ✅ |
| Recruiter action | < 1s | ✅ |
| Candidate sees update | < 5s | ✅ |
| Polling interval | 2s/5s | ✅ |
| Network per request | ~1KB | ✅ |

---

## 🔧 Configuration

### Required
```bash
# Backend/.env
GROQ_API_KEY=your_key_here
```

### Optional
```typescript
// frontend/src/pages/candidate/Applications.tsx
// Line ~50: Evaluation polling interval
}, 2000)  // Change to 3000 for 3 seconds

// Line ~70: Action polling interval
}, 5000)  // Change to 10000 for 10 seconds
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Evaluation never completes | Check GROQ_API_KEY, check logs |
| Recruiter buttons don't work | Check browser console, check permissions |
| Candidate doesn't see update | Check polling (Network tab), check DB |
| API returns 403 | Recruiter doesn't own the job |
| API returns 404 | Evaluation not found |

---

## 📚 Documentation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| README_EVALUATION_FIX.md | Overview | 5 min |
| IMPLEMENTATION_SUMMARY.md | What changed | 10 min |
| FLOW_DIAGRAM.md | Visual flow | 5 min |
| EVALUATION_FLOW_FIX.md | Technical details | 20 min |
| QUICK_START_TESTING.md | Testing guide | 10 min |
| API_TESTING_CURL.md | API reference | 15 min |
| CHANGES_CHECKLIST.md | Verification | 10 min |
| QUICK_REFERENCE.md | This card | 2 min |

---

## ✅ Deployment Checklist

- [ ] GROQ_API_KEY set
- [ ] Database running
- [ ] Backend running: `python Backend/run.py`
- [ ] Frontend running: `npm run dev`
- [ ] Test script passes: `python Backend/test_evaluation_flow.py`
- [ ] Manual testing done
- [ ] Logs configured
- [ ] Monitoring set up

---

## 🎯 Key Endpoints

### Candidate
```
GET  /api/candidate/evaluations              # List all
GET  /api/candidate/evaluations/{id}         # Get one (polling)
POST /api/jobs/{id}/express-interest         # Express interest
DELETE /api/candidate/evaluations/{id}       # Withdraw
GET  /api/evaluations/{id}/feedback          # Get feedback
```

### Recruiter
```
GET  /api/evaluations?job_id={id}            # List for job
GET  /api/evaluations/{id}                   # Get one
POST /api/evaluate                           # Trigger evaluation
POST /api/recruiter/action                   # Shortlist/Reject
POST /api/evaluations/{id}/action            # Alternative action
```

---

## 🔐 HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Recruiter action updated |
| 202 | Accepted | Evaluation started |
| 400 | Bad request | Missing fields |
| 401 | Unauthorized | No token |
| 403 | Forbidden | Wrong recruiter |
| 404 | Not found | Evaluation not found |

---

## 📱 Frontend Components

### Candidate
- **Applications.tsx** - Shows evaluations with polling
  - Polls every 2s for evaluation status
  - Polls every 5s for recruiter action
  - Shows score, recommendation, feedback

### Recruiter
- **Candidates.tsx** - Shows candidates with actions
  - Shortlist/Reject buttons
  - Refreshes after action
  - Shows loading state

---

## 🔄 Polling Strategy

### Evaluation Polling (2 seconds)
```
Active: While eval_status = 'pending' or 'running'
Stops: When eval_status = 'done' or 'error'
Endpoint: GET /candidate/evaluations/{id}
```

### Action Polling (5 seconds)
```
Active: Always (while on Applications page)
Checks: recruiter_action field
Endpoint: GET /candidate/evaluations
```

---

## 📧 Notifications

### When Shortlisted
- Type: `shortlisted`
- Title: "You've been shortlisted for..."
- Body: "A recruiter shortlisted you for..."
- Link: `/candidate/applications`

### When Rejected
- Type: `status_changed`
- Title: "Application update: ..."
- Body: "Your evaluation for ... was not selected"
- Link: `/candidate/applications`

---

## 🚨 Common Errors

### "Evaluation not found" (404)
```
Cause: Wrong evaluation ID
Fix: Check evaluation ID in URL
```

### "Forbidden" (403)
```
Cause: Recruiter doesn't own the job
Fix: Verify recruiter owns the job
```

### "Invalid action" (400)
```
Cause: Wrong action value
Fix: Use 'shortlist', 'reject', or 'reset'
```

### "Authentication required" (401)
```
Cause: No token or invalid token
Fix: Login and get new token
```

---

## 💡 Tips

1. **Use browser DevTools Network tab** to see API requests
2. **Check Backend logs** for detailed error messages
3. **Run test script** to verify everything works
4. **Use cURL** to test API endpoints directly
5. **Monitor polling** in Network tab to verify intervals

---

## 🎓 Learning Path

1. **Day 1:** Read README_EVALUATION_FIX.md + FLOW_DIAGRAM.md
2. **Day 2:** Run automated test + manual testing
3. **Day 3:** Review code changes in Backend/api.py
4. **Day 4:** Review code changes in frontend/src/pages/
5. **Day 5:** Deploy to production

---

## 📞 Quick Help

### "How do I test this?"
→ Run: `python Backend/test_evaluation_flow.py`

### "How do I deploy this?"
→ Read: IMPLEMENTATION_SUMMARY.md → Deployment Checklist

### "How do I understand the flow?"
→ Read: FLOW_DIAGRAM.md

### "How do I test the API?"
→ Read: API_TESTING_CURL.md

### "What changed?"
→ Read: CHANGES_CHECKLIST.md

---

## 🎯 Success Criteria

✅ Evaluation completes in < 30 seconds  
✅ Recruiter action updates in < 1 second  
✅ Candidate sees update in < 5 seconds  
✅ No errors in logs  
✅ All tests pass  
✅ Notifications sent  
✅ Toast messages appear  

---

## 📊 Metrics to Monitor

- Evaluation completion time
- Recruiter action response time
- Polling request frequency
- Error rate
- Database query time
- API response time

---

## 🔗 Related Files

- Backend/agents/__init__.py - Evaluation pipeline
- Backend/api.py - API endpoints
- Backend/models.py - Database models
- frontend/src/pages/candidate/Applications.tsx - Candidate UI
- frontend/src/pages/recruiter/Candidates.tsx - Recruiter UI

---

## 📝 Notes

- All times are in UTC
- Polling intervals are configurable
- Error messages are user-friendly
- Notifications are optional (email)
- Database schema unchanged

---

**Version:** 1.0  
**Status:** Production Ready  
**Last Updated:** January 2024  

**Start with:** README_EVALUATION_FIX.md
