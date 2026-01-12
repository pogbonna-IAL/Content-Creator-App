# Implementation Roadmap: Performance & Tiered Pricing

## Overview
This document provides a step-by-step implementation guide for optimizing content generation speed and implementing tiered pricing.

---

## Phase 1: Database Foundation (Week 1)

### Step 1.1: Add Subscription Models to Database
**File:** `src/content_creation_crew/database.py`

1. Import models from `database_models_subscription.py`
2. Add relationships to User model:
   ```python
   subscription = relationship("UserSubscription", back_populates="user", uselist=False)
   ```
3. Update `init_db()` to create new tables

### Step 1.2: Create Database Migration
**Command:**
```bash
cd content_creation_crew
alembic revision --autogenerate -m "add_subscription_tables"
alembic upgrade head
```

### Step 1.3: Initialize Tier Data
**Create script:** `scripts/init_tiers.py`
- Load tiers from `config/tiers.yaml`
- Insert into `subscription_tiers` table
- Set all existing users to 'free' tier

---

## Phase 2: Service Layer (Week 2)

### Step 2.1: Implement Subscription Service
**File:** `src/content_creation_crew/services/subscription_service.py` ✅ (Created)

**Test the service:**
```python
# Test script
from services.subscription_service import SubscriptionService
from database import get_db

db = next(get_db())
service = SubscriptionService(db)
tier = service.get_user_tier(user_id=1)
print(f"User tier: {tier}")
```

### Step 2.2: Create Usage Service
**File:** `src/content_creation_crew/services/usage_service.py`

```python
class UsageService:
    def get_current_period_usage(self, user_id: int, content_type: str) -> int:
        # Implementation
        
    def increment_usage(self, user_id: int, content_type: str):
        # Implementation
        
    def reset_period_usage(self, user_id: int):
        # Called when billing period renews
```

---

## Phase 3: Middleware & API Updates (Week 3)

### Step 3.1: Implement Tier Middleware
**File:** `src/content_creation_crew/middleware/tier_middleware.py` ✅ (Created)

### Step 3.2: Update Generate Endpoint
**File:** `api_server.py`

**Changes needed:**
1. Import subscription service and middleware
2. Add tier check before generation
3. Pass tier to ContentCreationCrew
4. Record usage after successful generation

**Example:**
```python
@app.post("/api/generate")
async def generate_content(
    request: TopicRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from content_creation_crew.services.subscription_service import SubscriptionService
    
    subscription_service = SubscriptionService(db)
    user_tier = subscription_service.get_user_tier(current_user.id)
    
    # Check usage limits
    has_access, remaining = subscription_service.check_usage_limit(
        current_user.id, 'blog'
    )
    
    if not has_access:
        raise HTTPException(403, "Usage limit reached")
    
    # Create crew with tier
    crew = ContentCreationCrew(tier=user_tier)
    
    # ... rest of generation logic
    
    # Record usage after success
    subscription_service.record_usage(current_user.id, 'blog')
```

### Step 3.3: Update Crew Class for Tier Support
**File:** `src/content_creation_crew/crew.py`

**Changes:**
1. Accept `tier` parameter in `__init__`
2. Select model based on tier
3. Filter tasks based on tier and requested content types
4. Use tier-specific process mode

---

## Phase 4: Performance Optimizations (Week 4)

### Step 4.1: Implement Parallel Processing
**File:** `src/content_creation_crew/crew.py`

Change:
```python
process=Process.sequential  # Current
```
To:
```python
process=Process.hierarchical  # For better parallel execution
```

### Step 4.2: Optimize Content Extraction
**File:** `api_server.py`

Replace file-based extraction with direct result extraction:
```python
def extract_content_direct(result) -> str:
    """Extract content directly from CrewAI result"""
    if hasattr(result, 'tasks_output') and result.tasks_output:
        # Get editing task output (main content)
        for task in result.tasks_output:
            if hasattr(task, 'agent') and 'editor' in str(task.agent).lower():
                if hasattr(task, 'output'):
                    return str(task.output)
    return ""
```

### Step 4.3: Add Content Caching
**File:** `src/content_creation_crew/services/cache_service.py`

```python
import hashlib
import json
from typing import Optional
import time

class ContentCache:
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, topic: str) -> Optional[str]:
        key = self._get_key(topic)
        entry = self.cache.get(key)
        
        if entry and time.time() - entry['timestamp'] < self.ttl:
            return entry['content']
        
        return None
    
    def set(self, topic: str, content: str):
        key = self._get_key(topic)
        self.cache[key] = {
            'content': content,
            'timestamp': time.time()
        }
    
    def _get_key(self, topic: str) -> str:
        return hashlib.md5(topic.lower().strip().encode()).hexdigest()
```

### Step 4.4: Implement Tier-Based Model Selection
**File:** `src/content_creation_crew/crew.py`

```python
def __init__(self, tier: str = 'free'):
    tier_config = self._load_tier_config()
    model = tier_config.get(tier, {}).get('model', 'ollama/llama3.2:1b')
    
    self.llm = LLM(
        model=model,
        base_url="http://localhost:11434",
        config={
            "timeout": 1800.0,
            "request_timeout": 1800.0,
            "connection_timeout": 60.0,
        }
    )
```

---

## Phase 5: Frontend Integration (Week 5)

### Step 5.1: Create Subscription Context
**File:** `web-ui/contexts/SubscriptionContext.tsx`

```typescript
interface SubscriptionContextType {
  tier: string
  usage: UsageStats
  limits: TierLimits
  refreshSubscription: () => Promise<void>
}

export function SubscriptionProvider({ children }) {
  // Fetch subscription data
  // Provide to components
}
```

### Step 5.2: Add Usage Display Component
**File:** `web-ui/components/UsageStats.tsx`

Display:
- Current tier
- Usage per content type
- Remaining generations
- Upgrade prompts

### Step 5.3: Add Tier Badge Component
**File:** `web-ui/components/TierBadge.tsx`

Show tier badge in navbar/user menu

### Step 5.4: Update Generate Button
**File:** `web-ui/app/page.tsx`

- Check usage before generation
- Show upgrade prompt if limit reached
- Display usage stats

---

## Phase 6: Subscription Management API (Week 6)

### Step 6.1: Create Subscription Routes
**File:** `src/content_creation_crew/subscription_routes.py`

Endpoints:
- `GET /api/subscription/current` - Get current subscription
- `GET /api/subscription/usage` - Get usage stats
- `POST /api/subscription/upgrade` - Upgrade subscription
- `POST /api/subscription/cancel` - Cancel subscription

### Step 6.2: Add to API Server
**File:** `api_server.py`

```python
from content_creation_crew.subscription_routes import router as subscription_router
app.include_router(subscription_router)
```

---

## Phase 7: Payment Integration (Week 7-8)

### Step 7.1: Integrate Stripe
**File:** `src/content_creation_crew/payment_service.py`

- Create Stripe customer
- Create subscription
- Handle webhooks
- Update subscription status

### Step 7.2: Create Webhook Handler
**File:** `api_server.py`

```python
@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    # Handle Stripe events
    # Update subscription status
    # Reset usage on renewal
```

---

## Testing Checklist

### Performance Testing
- [ ] Measure generation time before/after optimizations
- [ ] Test cache hit rates
- [ ] Verify parallel processing works
- [ ] Test with different tier models

### Tier Testing
- [ ] Free tier: Only blog, 5 generations max
- [ ] Basic tier: Blog + social, 50 each
- [ ] Pro tier: All types, unlimited
- [ ] Enterprise: All features, custom model

### Integration Testing
- [ ] Usage tracking increments correctly
- [ ] Limits enforced properly
- [ ] Tier upgrades work
- [ ] Payment webhooks process correctly

---

## Migration Strategy

1. **Backward Compatibility**
   - All existing users default to 'free' tier
   - No breaking changes to existing API

2. **Gradual Rollout**
   - Implement behind feature flags
   - Test with small user group first
   - Monitor performance metrics

3. **Data Migration**
   - Script to initialize tiers
   - Set all users to free tier
   - No data loss

---

## Success Metrics

### Performance
- Free tier: < 3 minutes average
- Paid tiers: < 5 minutes average
- Cache hit rate: > 30%

### Business
- Free → Paid conversion: Track
- Usage per tier: Monitor
- Churn rate: Track

---

## Next Steps

1. Review this plan with team
2. Set up development environment
3. Start with Phase 1 (Database)
4. Test each phase before moving to next
5. Deploy incrementally






