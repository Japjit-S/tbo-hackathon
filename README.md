# Adaptive Trust & Credit Intelligence Engine

A comprehensive fraud prevention and credit risk management system for B2B travel platforms. This system uses an adaptive trust model that evolves based on agency behavior, combined with behavioral anomaly detection and real-time risk evaluation.

---

## 📋 System Overview

The engine evaluates agencies across **3 trust dimensions**:
- **Financial Discipline (40%)** - Payment reliability, credit utilization, defaults
- **Behavioral Stability (35%)** - Booking patterns, velocity, consistency
- **Operational Legitimacy (25%)** - Account maturity, verification, compliance

**Credit Limits** are dynamically calculated based on composite trust:
- Formula: `$5,000 + ((composite_score - 55) / 5) * $5,000`
- Score 55 = $5K, Score 60 = $10K, Score 75 = $25K, Score 90 = $40K

**Risk Evaluation** uses behavioral anomaly detection + trust context:
- Formula: `risk = (base_anomaly × 0.40) + (trust_modifier × 0.35) + (fraud_signals × 0.25)`
- Detects 5 behavioral anomalies: amount deviation, timing, geography, pattern breaks, exposure velocity
- Monthly adaptive evaluation: strict baseline Month 1, personalized Month 2+

---

## 📁 File Structure

### Core Infrastructure Files

#### **1. `long_term_trust_model.py`** (350+ lines)
**Purpose:** Core trust evolution engine with credit limit calculation

**Key Classes:**
- `FinancialDisciplineFactors` - Tracks payment ratios, credit utilization, defaults, chargebacks
- `BehavioralStabilityFactors` - Tracks booking frequency, velocity spikes, cancellations, location diversity
- `OperationalLegitimacyFactors` - Tracks account age, KYC verification, business registration, API usage
- `TrustSnapshot` - Captures trust state at a point in time
- `LongTermTrustModel` - Main model coordinating all factors

**Key Methods:**
- `get_composite_trust_score()` - Returns weighted 0-100 score
- `get_monthly_credit_limit()` - Calculates credit limit from trust score
- `get_exposure_ratio()` - Outstanding / credit limit (0-1)
- `update_*_factors()` - Update factors in each dimension
- `apply_positive_activity()` - Boost trust (on-time payment, verified docs)
- `apply_negative_incident()` - Reduce trust (missed payment, chargeback, fraud)
- `add_snapshot()` - Create historical snapshot for trend analysis

**Score Calculation:**
- Financial: 40% (on-time ratio 45%, utilization 35%, defaults 15%, chargebacks 5%)
- Behavioral: 35% (velocity 40%, frequency 25%, cancellation 25%, diversity 10%)
- Operational: 25% (age 40%, verification 30%, geo diversity 20%, API usage 10%)

**Baseline:** All agencies start at composite score **55** with neutral factors

---

#### **2. `agency_database.py`** (550+ lines)
**Purpose:** SQLite persistence layer for agencies, factors, transactions, profiles

**Database Tables:**
- `agencies` - Agency metadata (ID, creation date, current trust score, risk level)
- `financial_factors` - Financial metrics per agency
- `behavioral_factors` - Behavioral metrics per agency
- `operational_factors` - Operational metrics per agency
- `trust_snapshots` - Historical trust scores for trend analysis
- `transactions` - Complete transaction log (bookings, payments)
- `agency_risk_profiles` - Monthly personalized thresholds (month 2+)
- `agency_behavior_profiles` - Learned behavior patterns (amounts, frequency, geos, times)

**Key Methods:**
- `save_agency()` / `get_agency()` - Persist/restore full agency state
- `save_transaction()` / `get_agency_transactions()` - Log and retrieve transaction history
- `save_trust_snapshot()` / `get_agency_trust_history()` - Track evolution over time
- `save_risk_profile()` / `get_risk_profile()` - Store monthly personalized thresholds
- `save_behavior_profile()` / `get_behavior_profile()` - Store learned behavior patterns

**Transaction Storage:**
Each transaction includes: ID, agency_id, type (BOOKING/PAYMENT), amount, status, timestamp, notes

---

#### **3. `trust_manager.py`** (250+ lines)
**Purpose:** High-level facade linking trust model and database

**Key Classes:**
- `TrustManager` - Coordinates between LongTermTrustModel, AgencyDatabase, and profiles

**Key Methods:**
- `create_agency()` - Create new agency with baseline trust (55)
- `get_agency()` - Retrieve agency (cached in memory)
- `update_*_factors()` - Update and persist factors
- `apply_positive_activity()` / `apply_incident()` - Trust boosts/penalties
- `get_trust_score()` / `get_agency_status()` - Current state queries
- `calculate_and_save_risk_profile()` - Learn personalized thresholds after month 1
- `calculate_and_save_behavior_profile()` - Learn behavior patterns from transactions
- `generate_risk_report()` - Detailed risk assessment narrative

**Features:**
- In-memory caching for performance
- Automatic database persistence
- Clean separation between model and database logic

---

#### **4. `agency_behavior_profile.py`** (NEW - 400+ lines)
**Purpose:** Learns and detects behavioral anomalies for real-time risk evaluation

**Key Classes:**
- `TransactionRecord` - Single transaction for pattern analysis
- `AgencyBehaviorProfile` - Tracks behavioral patterns and detects anomalies

**Learned Patterns:**
- Booking amount statistics (avg, std_dev, min, max, trend)
- Booking frequency (bookings per week, days between bookings)
- Timing patterns (typical booking hours of day)
- Geographic patterns (known locations, distribution)
- Recent transactions (last 20 for pattern comparison)
- Payment cycles (days to recover, ratio)
- Merchant categories (types of bookings)

**Anomaly Detection Methods:**
- `calculate_amount_deviation()` - Z-score: is amount outside normal range?
- `calculate_frequency_deviation()` - Is booking frequency unusual?
- `is_timing_anomaly()` - Is booking at atypical time?
- `is_geo_anomaly()` - Is location outside known geos?
- `calculate_pattern_break()` - Does amount break recent pattern?
- `calculate_exposure_velocity()` - Is exposure growing too fast?

**Learning Threshold:** Minimum 5 transactions before anomaly detection active

---

#### **5. `booking_risk_evaluator.py`** (600+ lines)
**Purpose:** Real-time risk evaluation using behavioral anomalies + trust context

**Key Classes:**
- `BookingRequest` - Incoming booking request (agency_id, amount, location, device, timestamp, merchant_category)
- `RiskSignal` - Traditional risk indicator (velocity, value deviation, device, utilization, maturity)
- `BehavioralAnomaly` - Behavioral pattern deviation (amount, timing, geo, pattern, exposure)
- `BookingRiskAssessment` - Complete evaluation result with all signals and anomalies
- `BookingRiskEvaluator` - Main evaluator engine

**Evaluation Modes:**
- **Month 1 (Days 0-29):** BASELINE - Uses generic/strict thresholds
- **Month 2+ (Days 30+):** PERSONALIZED - Uses learned behavior patterns

**5 Traditional Risk Signals:**
1. **velocity_spike** - Abnormal booking frequency (>1.5x)
2. **value_deviation** - Unusual booking amount (too high/low)
3. **device_anomaly** - Unknown or suspicious device
4. **credit_utilization** - High % of credit limit used (>80%)
5. **account_maturity** - New accounts (<30 days)

**5 Behavioral Anomalies:**
1. **amount_deviation** - Amount outside learned range (Z-score)
2. **timing_anomaly** - Booking at unusual hour
3. **geo_anomaly** - Location outside known geos
4. **pattern_break** - Amount breaks recent transaction pattern
5. **exposure_velocity** - Credit exposure growing too fast

**Risk Scoring Formula:**
```
risk_score = (base_anomaly × 0.40) + (trust_modifier × 0.35) + (fraud_signals × 0.25)

where:
- base_anomaly = average behavioral anomaly severity (0-100)
- trust_modifier = (100 - trust_score) × 0.7
- fraud_signals = average risk signal severity (0-100)
```

**Approval Decisions:**
- **Approve** (<20 risk) - Low risk, proceed
- **Approve with Monitoring** (20-35 risk) - Acceptable with monitoring
- **Reduce Exposure** (35-50 risk) - Cap at 50% of normal limit
- **Escalate** (50-65 risk) - Manual review required
- **Restrict** (>65 risk) - Block transaction, notify compliance

**Key Methods:**
- `evaluate()` - Run full risk assessment (signals + anomalies + trust)
- `_detect_risk_signals()` - Identify traditional fraud signals
- `_detect_behavioral_anomalies()` - Identify behavioral deviations
- `_calculate_risk_score()` - Compute composite risk using new formula
- `_make_decision()` - Convert risk to approval decision

---

#### **6. `transaction_processor.py`** (350+ lines)
**Purpose:** End-to-end transaction orchestration (3-step flow)

**Key Classes:**
- `TransactionProcessor` - Orchestrates complete transaction lifecycle

**3-Step Transaction Flow:**
1. **Evaluate** - Use BookingRiskEvaluator to assess risk (with behavioral anomalies)
2. **Execute** - If approved, create transaction record
3. **Update** - Modify trust model based on outcome

**Key Methods:**
- `process_booking()` - Process booking (BUY transaction)
  - Runs full risk evaluation (signals + anomalies)
  - Executes if approved
  - Updates behavioral factors
  - Returns record with all evaluation details
  
- `process_payment()` - Process payment (SELL transaction)
  - Reduces outstanding amount
  - Improves financial metrics
  - Updates database
  - Returns record with trust improvement

- `get_agency_status()` - Comprehensive agency status
- `get_transaction_summary()` - Summary of all transactions
- `get_agency_transactions()` - Transactions for specific agency

**Transaction Record:** Includes all evaluation details (risk_score, decision, anomalies, reasoning)

---

### Testing & Simulation File

#### **7. `test_simulation.py`** (450+ lines)
**Purpose:** Interactive manual testing system with buy/sell transactions

**Key Classes:**
- `TransactionSimulator` - Interactive simulator for manual testing

**Key Methods:**
- `create_agency()` - Create new agency (starts at composite score 55)
- `process_buy_transaction()` - Process booking with full output
  - Shows all detected anomalies with severity %
  - Displays risk signals
  - Shows base anomaly score and risk score breakdown
  - Updates trust model
  
- `process_sell_transaction()` - Process payment
  - Shows outstanding reduction
  - Displays trust improvement
  - Updates financial factors
  
- `show_agency_status()` - Display agency dashboard
  - Trust score and risk level
  - All 3 dimension scores
  - Monthly credit limit and exposure ratio
  - Recent transaction history
  
- `advance_date()` - Simulate time passing (increments account age)
- `show_summary()` - System-wide status summary

**Interactive Menu:**
```
1. Create new agency
2. Process BUY transaction (booking)
3. Process SELL transaction (payment)
4. View agency status
5. Advance date
6. Show summary
7. Exit
```

**Baseline Initialization:**
- All agencies start at composite score 55
- All factors initialized neutrally (0 or 50% baseline)
- Factors evolve based on transaction history
- No prior assumptions about agency reliability

**Output Example:**
```
[STEP 1] Real-Time Risk Evaluation
  Evaluation Mode: BASELINE - Using generic thresholds (Month 1)
  Monthly Credit Limit: $5,000.00
  Current Exposure: 0.0%
  
  Risk Score: 35.50/100
  Base Anomaly Score: 12.50/100
  Decision: REDUCE_EXPOSURE
  
  Behavioral Anomalies:
    • amount_deviation (45%): Amount $15,000 is 45% unusual (avg: $3,500)
    • timing_anomaly (60%): Booking at 02:30 is unusual for this agency
  
  Risk Signals:
    • account_maturity: New account (5 days old)
```

---

## 🔄 Data Flow

```
User Input (Manual)
        ↓
TransactionSimulator (User Interface)
        ↓
TransactionProcessor (Orchestration)
    ↙       ↘
BookingRiskEvaluator          TrustManager
  ↙     ↘                        ↙        ↘
Risk    Behavioral       LongTermTrust   AgencyDatabase
Signals Anomalies        Model           + Transactions
                                         + Profiles
                ↓
         SQLite Persistence
         (Full History Stored)
```

---

## 💾 Database Schema

### Agencies Table
```sql
agency_id | created_at | updated_at | current_trust_score | risk_level
MERCHANT  | 2026-03-01 | 2026-03-01 | 55.00               | MODERATE
```

### Financial Factors Table
```sql
agency_id | on_time_ratio | utilization | outstanding | defaults | chargebacks
MERCHANT  | 20.0          | 50.0        | 0.0          | 0        | 0.0
```

### Transactions Table (Complete History!)
```sql
transaction_id      | agency_id | type    | amount | status   | timestamp
TXN_BUY_MERCHANT_1  | MERCHANT  | BOOKING | 5000.0 | APPROVED | 2026-03-01 10:30
TXN_PAY_MERCHANT_1  | MERCHANT  | PAYMENT | 3000.0 | PROCESS  | 2026-03-01 15:45
```

### Behavior Profiles Table
```sql
agency_id | avg_booking_amount | std_dev | known_geos | merchant_categories | transaction_count
MERCHANT  | 3500.0             | 850.5  | ["US-CA"]  | ["TRAVEL"]          | 12
```

### Risk Profiles Table (Monthly)
```sql
agency_id | month_number | avg_booking_value | normal_frequency | signal_weights
MERCHANT  | 2            | 3500.0            | 2.5              | {...}
```

---

## 🎯 Key Concepts

### Trust Score (0-100)
- **Composite:** Weighted average of 3 dimensions (Financial 40%, Behavioral 35%, Operational 25%)
- **Baseline:** 55 (new agencies)
- **Risk Assessment:**
  - 80+ = LOW RISK
  - 60-80 = MODERATE RISK
  - 40-60 = HIGH RISK
  - <40 = CRITICAL RISK

### Monthly Credit Limit
- **Formula:** `$5,000 + ((composite_score - 55) / 5) * $5,000`
- **Examples:**
  - Score 55 → $5,000
  - Score 60 → $10,000
  - Score 75 → $25,000
  - Score 90 → $40,000
- **Exposure Ratio:** outstanding_amount / monthly_limit (0-1)

### Risk Score (0-100) - NEW BEHAVIORAL MODEL
**No longer:** `risk = 100 - trust`  
**Now:** `risk = (behavioral_anomaly × 0.40) + (trust_modifier × 0.35) + (fraud_signals × 0.25)`

**Decision Thresholds:**
- 0-20 = Approve
- 20-35 = Approve with monitoring
- 35-50 = Reduce exposure
- 50-65 = Escalate for review
- 65+ = Restrict

### Evaluation Modes
**Month 1 (BASELINE):**
- Strict generic thresholds
- All agencies treated equally (unknowns)
- Can't comment reliably yet
- Account maturity signal severe (1.0x)

**Month 2+ (PERSONALIZED):**
- Learned thresholds from transaction history
- Agency-specific anomaly detection
- Adjusted signal weights
- Account maturity signal reduced (0.3x)

### Behavioral Anomalies Detected
1. **Amount Deviation** - Z-score analysis vs average
2. **Timing Anomaly** - Is booking at unusual hour?
3. **Geographic Anomaly** - Is location outside known geos?
4. **Pattern Break** - Does this break recent pattern?
5. **Exposure Velocity** - Is exposure growing too fast?

Each with severity 0-1 (converted to %)

### Transaction History
- **Every booking and payment stored** in database
- Used for behavior profile learning
- Enables pattern analysis
- Complete audit trail
- Queryable by agency

### Positive Activities (Trust Boost)
- `on_time_payment` → +2% on-time ratio
- `completed_booking` → +0.5 booking frequency
- `verified_document` → Document verification flag
- `registered_business` → Business registration flag

### Negative Incidents (Trust Penalty)
- `missed_payment` → -5% on-time ratio
- `chargeback` → +10% chargeback ratio
- `high_velocity_booking` → 1.0-2.0x velocity spike
- `booking_cancellation` → +5% cancellation ratio
- `fraud_detection` → 2.0-3.0x velocity spike + default

---

## 🚀 Getting Started

### 1. Run the Interactive Simulator
```bash
python test_simulation.py
```

### 2. Create an Agency
```
Select option: 1
Agency ID: ACME_TRAVEL_001
✓ Agency created with baseline trust: 55.00/100
Monthly Credit Limit: $5,000.00
```

### 3. Process Transactions (Different Patterns)
```
Select option: 2  # Buy transaction
Agency ID: ACME_TRAVEL_001
Booking amount: 3500  # Normal
Location: US-CA
[BASELINE mode, no anomalies, LOW risk, APPROVE]

---

Select option: 2  # Buy transaction
Agency ID: ACME_TRAVEL_001
Booking amount: 15000  # 4.3x normal!
Location: EU-UK  # Outside known geo!
[Amount deviation (75%) + geo anomaly (100%) detected, HIGH risk]
```

### 4. Monitor Status & Credit Limit
```
Select option: 4
Agency ID: ACME_TRAVEL_001
Trust Score: 58.20/100, Risk Level: MODERATE
Monthly Credit Limit: $6,200.00
Current Outstanding: $3,500.00
Exposure Ratio: 56.5%
```

### 5. Advance Time (Days)
```
Select option: 5
Days to advance: 30
⏰ Date advanced to: 2026-03-31
[Account age: 0 → 30, switches to PERSONALIZED evaluation mode]
```

### 6. After Month 1: Personalized Behavior Detection
```
Select option: 2  # Same $3,500 booking
Agency ID: ACME_TRAVEL_001
[PERSONALIZED mode activated]
[No anomalies - matches learned pattern exactly]
[BASELINE risk score was 35, now risk score: 18, APPROVE]
```

---

## 📊 Example Scenarios

### Scenario 1: New Agency Starts Safe
```
Day 1: Create agency
  Score: 55/100
  Limit: $5,000
  Mode: BASELINE (strict)

Day 1: Book $3,500 (US-CA, 10 AM)
  Anomalies: None (first transaction, no pattern yet)
  Signals: account_maturity (severity 1.0)
  Risk: 35/100
  Decision: REDUCE_EXPOSURE

Day 2: Book $3,200 (US-CA, 9 AM) - Similar to Day 1
  Anomalies: None (starting to build pattern)
  Signals: account_maturity
  Risk: 35/100
  Decision: REDUCE_EXPOSURE

Day 30: 10 bookings at $3,000-3,500 average
  Score: 62/100 (improved through bookings)
  Limit: $10,600
  → Switches to PERSONALIZED evaluation

Day 31: Book $3,300 (US-CA, 10 AM)
  Anomalies: None (matches learned pattern perfectly)
  Signals: account_maturity now lower severity
  Risk: 18/100
  Decision: APPROVE

Day 31: Book $20,000 (EU-DE, 2 AM)
  Anomalies: 
    - amount_deviation (85%)
    - geo_anomaly (100%)
    - timing_anomaly (90%)
  Risk: 65/100
  Decision: RESTRICT
```

### Scenario 2: Pattern-Based Fraud Detection
```
Agency History (5 bookings):
  - $3,500 (US-CA, 10 AM)
  - $3,200 (US-CA, 11 AM)
  - $3,800 (US-NY, 9 AM)
  - $3,100 (US-CA, 10 AM)
  - $3,400 (US-CA, 10 AM)

Learned Profile:
  Avg: $3,400, StdDev: $300
  Known Geos: {US-CA, US-NY}
  Typical Hours: {9, 10, 11}

New Booking: $18,000 (EU-UK, 3 AM)
Anomalies Detected:
  - amount_deviation: (18000-3400)/300 = 48.7x std dev! Severity: 1.0 (100%)
  - geo_anomaly: EU-UK not in {US-CA, US-NY}. Severity: 1.0 (100%)
  - timing_anomaly: 3 AM not in {9,10,11}. Severity: 1.0 (100%)
  - exposure_velocity: Would use 72% of $10,600 limit. Severity: 0.8 (80%)

Base Anomaly Score: avg(1.0, 1.0, 1.0, 0.8) × 100 = 95/100
Risk Formula: (95×0.40) + (trust_modifier×0.35) + (signals×0.25)
If trust=60: Risk = 38 + 28 + 10 = 76/100
Decision: RESTRICT (Block transaction, notify compliance)
```

---

## 🔐 Risk Thresholds & Decisions

| Risk Score | Decision | Action |
|-----------|----------|--------|
| < 20 | APPROVE | Proceed with booking |
| 20-35 | APPROVE_WITH_MONITORING | Approve + flag for review |
| 35-50 | REDUCE_EXPOSURE | Cap at 50% of normal limit |
| 50-65 | ESCALATE | Manual review required |
| > 65 | RESTRICT | Block transaction, notify compliance |

---

## 📈 Trust Evolution Timeline

**Day 1:** Agency created
- Trust: 55/100, Limit: $5,000
- Factors: all neutral/baseline
- Mode: BASELINE (strict)

**Day 1:** $5,000 booking approved
- Trust: 55.50/100, Limit: $5,250 (+0.5% increase)
- Behavioral updated: frequency, velocity

**Day 2:** $3,000 payment processed
- Trust: 56.00/100, Limit: $5,400
- Financial improved: on-time ratio, utilization

**Day 3-30:** 8 more bookings at $3-4K
- Trust gradually increases with pattern
- Operational legitimacy increases (age: 0→30 days)
- On-time ratio improves with payments

**Day 30:** Trust reaches 65/100
- Limit: $15,000
- Mode switches: BASELINE → PERSONALIZED
- Behavior profile learned (avg $3,400, std dev $300, etc)
- Account maturity signal severity reduces from 1.0 to 0.3

**Day 31+:** Personalized evaluation active
- Same $3,400 booking now APPROVE (no anomalies, matches pattern)
- $20,000 booking now RESTRICT (5.9x std dev, multiple anomalies)
- Learned behavior makes evaluation smarter

---

## 🛠️ Configuration & Customization

### Trust Weights (in `long_term_trust_model.py`)
```python
composite_score = (
    financial_score * 0.40 +    # Can adjust
    behavioral_score * 0.35 +   # Can adjust
    operational_score * 0.25    # Can adjust
)
```

### Risk Calculation Weights (in `booking_risk_evaluator.py`)
```python
risk = (
    base_anomaly * 0.40 +       # Behavioral anomalies
    trust_modifier * 0.35 +     # Trust context
    fraud_signals * 0.25        # Traditional signals
)
```

### Credit Limit Formula (in `long_term_trust_model.py`)
```python
monthly_limit = 5000 + ((composite_score - 55) / 5) * 5000
```

### Signal Severities (in `booking_risk_evaluator.py`)
- Velocity spike: Max 1.5x penalty
- Value deviation: Max 1.0 severity
- Device anomaly: 0.3 fixed severity
- Credit utilization: Max 1.0 severity
- Account maturity: 1.0 (Month 1), 0.3 (Month 2+)

### Anomaly Thresholds (in `agency_behavior_profile.py`)
- Amount deviation: Z-score / 3.0 (normalize to 0-1)
- Frequency deviation: 2.0x or 0.5x is anomaly
- Timing anomaly: Outside learned hours = 1.0
- Geo anomaly: Outside known geos = 1.0
- Pattern break: 2 std devs = 1.0

---

## 📞 Advanced Features

### Multi-Month Learning
- Month 1: Generic thresholds, all agencies treated equally
- Month 2: Behavior learned, personalized anomaly detection
- Month 3+: Deep patterns from 60+ days of history

### Behavioral Indicators
- Learns: amounts, frequency, timing, locations, payment cycles
- Detects: deviations with statistical rigor (Z-scores)
- Adapts: thresholds personalized per agency
- Evolves: profiles update as more transactions accumulate

### Transaction Audit Trail
- Every booking and payment logged permanently
- Complete history available for review
- Pattern analysis based on full history
- Compliance-ready documentation

### Real-Time Decision Making
- Sub-second risk assessment
- Multiple anomaly detection (5 behavioral + 5 signals)
- Confidence scoring based on signal count
- Detailed reasoning provided with every decision

---

## 📝 Behavioral Anomaly Examples

```
Amount Deviation:
  Learned avg: $3,500, std dev: $400
  New booking: $12,000
  Z-score: (12000-3500)/400 = 21.25x!
  Severity: min(21.25/3, 1.0) = 1.0 (100%)
  Description: "Amount $12,000 is 100% unusual (avg: $3,500)"

Timing Anomaly:
  Learned hours: {9, 10, 11, 14, 15}
  New booking: 2:30 AM
  Severity: 1.0 (100%)
  Description: "Booking at 02:30 is unusual for this agency"

Geographic Anomaly:
  Learned geos: {US-CA, US-NY}
  New booking: EU-UK
  Severity: 1.0 (100%)
  Description: "Location EU-UK is outside known geos"

Pattern Break:
  Recent 5 bookings: [$3,200, $3,400, $3,100, $3,500, $3,300]
  Recent avg: $3,300, std dev: $150
  New booking: $8,000
  Z-score: (8000-3300)/150 = 31.3x!
  Severity: min(31.3/2, 1.0) = 1.0 (100%)
  Description: "Amount breaks recent pattern"

Exposure Velocity:
  Credit limit: $10,600
  Current outstanding: $2,000
  New booking: $8,000
  New exposure: 10000/10600 = 94.3%
  Severity: min((0.943-0.7)/0.3, 1.0) = 0.81 (81%)
  Description: "Credit exposure at critical 94.3%"
```

---

**Version:** 2.0 - Behavioral Risk Model  
**Last Updated:** March 1, 2026  
**Status:** Production Ready  
**Features:**
- ✅ Adaptive trust scoring (3 dimensions)
- ✅ Dynamic credit limits
- ✅ Behavioral anomaly detection (5 types)
- ✅ Monthly evaluation modes (baseline + personalized)
- ✅ Real-time risk assessment
- ✅ Complete transaction history
- ✅ Pattern learning from history
- ✅ Statistical anomaly detection (Z-scores)
- ✅ Interactive simulator


---

## 📋 System Overview

The engine evaluates agencies across **3 trust dimensions**:
- **Financial Discipline (40%)** - Payment reliability, credit utilization, defaults
- **Behavioral Stability (35%)** - Booking patterns, velocity, consistency
- **Operational Legitimacy (25%)** - Account maturity, verification, compliance

Each booking request is evaluated in real-time using 5 independent risk signals, combined with the agency's historical trust context to make approval decisions.

---

## 📁 File Structure

### Core Infrastructure Files

#### **1. `long_term_trust_model.py`** (300+ lines)
**Purpose:** Core trust evolution engine

**Key Classes:**
- `FinancialDisciplineFactors` - Tracks payment ratios, credit utilization, defaults, chargebacks
- `BehavioralStabilityFactors` - Tracks booking frequency, velocity spikes, cancellations, location diversity
- `OperationalLegitimacyFactors` - Tracks account age, KYC verification, business registration, API usage
- `TrustSnapshot` - Captures trust state at a point in time
- `LongTermTrustModel` - Main model that coordinates all factors and generates composite trust scores

**Key Methods:**
- `get_composite_trust_score()` - Returns 0-100 weighted score
- `update_*_factors()` - Update factors in each dimension
- `apply_positive_activity()` - Boost trust (on-time payment, verified docs, etc.)
- `apply_negative_incident()` - Reduce trust (missed payment, chargeback, fraud detection, etc.)
- `add_snapshot()` - Create historical snapshot for trend analysis
- `get_trust_narrative()` - Generate human-readable assessment

**Score Calculation:**
- Financial: 40% weight (on-time ratio, utilization, defaults, chargebacks)
- Behavioral: 35% weight (velocity, frequency, cancellation, diversity, trend)
- Operational: 25% weight (age, verification, registration, contact, API usage)

---

#### **2. `agency_database.py`** (400+ lines)
**Purpose:** SQLite persistence layer for agencies and trust data

**Key Classes:**
- `AgencyDatabase` - Manages all database operations

**Database Tables:**
- `agencies` - Agency metadata (ID, creation date, current trust score, risk level)
- `financial_factors` - Financial metrics per agency
- `behavioral_factors` - Behavioral metrics per agency
- `operational_factors` - Operational metrics per agency
- `trust_snapshots` - Historical trust scores for trend analysis
- `transactions` - Complete transaction log

**Key Methods:**
- `save_agency()` - Persist agency and all factors to database
- `get_agency()` - Retrieve and restore agency with all factors
- `save_trust_snapshot()` - Record trust state for history
- `get_agency_trust_history()` - Retrieve trust evolution over time
- `save_transaction()` - Log booking/payment transactions
- `get_agency_transactions()` - Retrieve transaction history
- `get_agencies_by_risk_level()` - Query agencies at specific risk levels

**Database Persistence:**
- Automatic SQLite initialization on first connection
- All agency updates persist across sessions
- Historical snapshots enable trend analysis

---

#### **3. `trust_manager.py`** (200+ lines)
**Purpose:** High-level facade linking trust model and database

**Key Classes:**
- `TrustManager` - Coordinates between LongTermTrustModel and AgencyDatabase

**Key Methods:**
- `create_agency()` - Create new agency with baseline trust
- `get_agency()` - Retrieve agency (cached in memory)
- `update_*_factors()` - Update and persist factors
- `apply_positive_activity()` - Apply trust boosts
- `apply_incident()` - Apply trust penalties
- `get_trust_score()` - Get current agency trust score
- `get_agency_status()` - Comprehensive agency status dictionary
- `generate_risk_report()` - Detailed risk assessment narrative
- `get_agency_history()` - Trust evolution over time
- `get_agency_transactions()` - Transaction history

**Features:**
- In-memory caching for performance
- Automatic database persistence
- Clean separation between model and database logic

---

#### **4. `booking_risk_evaluator.py`** (500+ lines)
**Purpose:** Real-time risk evaluation for booking requests

**Key Classes:**
- `BookingRequest` - Incoming booking request (agency_id, amount, location, device_id)
- `RiskSignal` - Individual risk indicator (type, severity 0-1, description)
- `BookingRiskAssessment` - Risk evaluation result (risk_score, decision, signals, reasoning)
- `BookingRiskEvaluator` - Main evaluator

**5 Risk Signals Detected:**
1. **velocity_spike** - Abnormal booking frequency spike (>1.5x normal)
2. **value_deviation** - Unusual booking amount (too high or too low)
3. **device_anomaly** - Unknown or suspicious device
4. **credit_utilization** - High percentage of credit limit used (>80%)
5. **account_maturity** - New accounts (<30 days old) are riskier

**Risk Scoring:**
- Base risk = 100 - trust_score (inverse relationship)
- Signal contributions add up to 30 points
- Combined score: 70% base + 30% signals
- Final score: 0-100

**Approval Decisions:**
- **Approve** (<20 risk) - Low risk, proceed
- **Approve with Monitoring** (20-35 risk) - Acceptable but flag for review
- **Reduce Exposure** (35-50 risk) - Cap transaction at 50% of normal limit
- **Escalate** (50-65 risk) - Manual review required
- **Restrict** (>65 risk) - Block transaction, notify compliance

**Key Methods:**
- `evaluate()` - Run full risk assessment
- `_detect_risk_signals()` - Identify all present signals
- `_calculate_risk_score()` - Compute composite risk (0-100)
- `_make_decision()` - Convert risk to approval decision
- `_calculate_confidence()` - Confidence in decision (0-100)
- `_build_reasoning()` - Human-readable explanation

---

#### **5. `transaction_processor.py`** (300+ lines)
**Purpose:** End-to-end transaction orchestration (3-step flow)

**Key Classes:**
- `TransactionProcessor` - Orchestrates complete transaction lifecycle

**3-Step Transaction Flow:**
1. **Evaluate** - Use BookingRiskEvaluator to assess risk
2. **Execute** - If approved, create transaction record
3. **Update** - Modify trust model based on outcome

**Key Methods:**
- `process_booking()` - Process booking (buy transaction)
  - Runs risk evaluation
  - Executes if approved
  - Updates behavioral factors (booking frequency, velocity)
  - Returns detailed record with decision reasoning
  
- `process_payment()` - Process payment (sell transaction)
  - Reduces outstanding amount
  - Improves on-time ratio
  - Reduces credit utilization
  - Returns record with trust improvement

- `get_agency_status()` - Comprehensive agency status
- `get_transaction_summary()` - Summary of all transactions
- `get_agency_transactions()` - Transactions for specific agency

**Transaction Log:**
- All transactions recorded with decisions and reasoning
- Enables audit trail and performance analysis
- Supports risk pattern detection

---

### Testing & Simulation File

#### **6. `test_simulation.py`** (400+ lines)
**Purpose:** Interactive manual testing system with buy/sell transactions

**Key Classes:**
- `TransactionSimulator` - Interactive simulator for manual testing

**Key Methods:**
- `create_agency()` - Create new agency with baseline neutral factors
- `process_buy_transaction()` - Process booking with full output
  - Shows risk evaluation details
  - Displays all detected signals
  - Prints decision reasoning
  - Updates trust model
  
- `process_sell_transaction()` - Process payment
  - Shows outstanding reduction
  - Displays trust improvement
  - Updates financial factors
  
- `show_agency_status()` - Display agency dashboard
  - Trust score and risk level
  - All 3 dimension scores
  - Financial/behavioral/operational details
  - Recent transaction history
  
- `advance_date()` - Simulate time passing (increments account age)
- `show_summary()` - System-wide status summary

**Interactive Menu:**
```
1. Create new agency
2. Process BUY transaction (booking)
3. Process SELL transaction (payment)
4. View agency status
5. Advance date
6. Show summary
7. Exit
```

**Baseline Initialization:**
- All agencies start with neutral factors (0 or 50% baseline)
- Factors evolve based on transaction history
- No prior assumptions about agency reliability

**Usage Example:**
```python
python test_simulation.py

# Create agency
→ Enter Agency ID: MERCHANT_001
✓ Agency created with baseline trust: 79.72/100

# Process buy transaction
→ Agency ID: MERCHANT_001
→ Booking amount: 5000
→ Location: US-CA
→ Notes: Travel package booking
[Full risk evaluation and trust update...]

# View status
→ Agency ID: MERCHANT_001
Trust Score: 79.95/100, Risk Level: LOW
Financial: 68.50/100, Behavioral: 85.00/100, Operational: 72.50/100

# Process payment
→ Agency ID: MERCHANT_001
→ Payment amount: 3000
✓ Payment processed, Outstanding: $5000 → $2000
  Trust improved: 79.95 → 80.18
```

---

## 🔄 Data Flow

```
User Input (Manual)
        ↓
TransactionSimulator (User Interface)
        ↓
TransactionProcessor (Orchestration)
    ↙       ↘
BookingRiskEvaluator    TrustManager
    ↓                       ↓
LongTermTrustModel    AgencyDatabase
    ↓                       ↓
Trust Calculation      SQLite Persistence
```

---

## 💾 Database Schema

### Agencies Table
```sql
agency_id (PK)    | created_at    | updated_at    | current_trust_score | risk_level
MERCHANT_001      | 2026-03-01    | 2026-03-01    | 79.72               | LOW
```

### Financial Factors Table
```sql
agency_id (PK) | on_time_ratio | utilization | outstanding | defaults | chargebacks
MERCHANT_001   | 50.0          | 0.0         | 0.0          | 0        | 0.0
```

### Behavioral Factors Table
```sql
agency_id (PK) | frequency | velocity | cancellation | locations | trend
MERCHANT_001   | 2.0       | 1.0      | 0.0          | 1         | stable
```

### Operational Factors Table
```sql
agency_id (PK) | age_days | geos      | verified | registered | contact_verified | api_usage
MERCHANT_001   | 0        | ["US-CA"] | false    | false      | false            | 0
```

### Trust Snapshots Table
```sql
id | agency_id   | timestamp     | financial | behavioral | operational | composite | notes
1  | MERCHANT_001| 2026-03-01    | 66.50     | 85.00      | 72.50        | 79.72     | Account created
```

### Transactions Table
```sql
transaction_id       | agency_id    | type    | amount | status   | timestamp     | notes
TXN_BUY_MERCH_001... | MERCHANT_001 | BOOKING | 5000.0 | APPROVED | 2026-03-01    | Travel package
```

---

## 🎯 Key Concepts

### Trust Score (0-100)
- **80+** = LOW RISK - Approve most bookings
- **60-80** = MODERATE RISK - Monitor and approve with caution
- **40-60** = HIGH RISK - Reduce exposure, manual review
- **<40** = CRITICAL RISK - Restrict bookings, investigate

### Risk Score (0-100)
Inverse of trust with signal amplification:
- 0-20 = Approve
- 20-35 = Approve with monitoring
- 35-50 = Reduce exposure
- 50-65 = Escalate for review
- 65+ = Restrict

### Positive Activities (Trust Boost)
- `on_time_payment` → +2% on-time ratio
- `completed_booking` → +0.5 booking frequency
- `verified_document` → Document verification flag
- `registered_business` → Business registration flag

### Negative Incidents (Trust Penalty)
- `missed_payment` → -5% on-time ratio
- `chargeback` → +10% chargeback ratio
- `high_velocity_booking` → 1.0-2.0x velocity spike
- `booking_cancellation` → +5% cancellation ratio
- `fraud_detection` → 2.0-3.0x velocity spike + default

---

## 🚀 Getting Started

### 1. Run the Interactive Simulator
```bash
python test_simulation.py
```

### 2. Create an Agency
```
Select option: 1
Agency ID: ACME_TRAVEL_001
✓ Agency created with baseline trust: 79.72/100
```

### 3. Process Transactions
```
Select option: 2  # Buy transaction
Agency ID: ACME_TRAVEL_001
Booking amount: 10000
Location: US-NY
Notes: Spring vacation packages
[Risk evaluation with 5 signals and decision...]

Select option: 3  # Sell transaction
Agency ID: ACME_TRAVEL_001
Payment amount: 5000
[Outstanding reduced, trust improved...]
```

### 4. Monitor Status
```
Select option: 4
Agency ID: ACME_TRAVEL_001
Trust Score: 82.15/100, Risk Level: LOW
[All dimensions displayed...]
```

### 5. Advance Time
```
Select option: 5
Days to advance: 30
⏰ Date advanced to: 2026-03-31
[Account ages incremented...]
```

---

## 📊 Output Examples

### Booking Approval with Reasoning
```
[STEP 1] Real-Time Risk Evaluation
  Agency: MERCHANT_001
  Value: $10,000.00
  Risk Score: 12.45/100
  Decision: APPROVE
  Confidence: 95.0%
  
  Risk Signals:
    • account_maturity: New account (5 days old)
  
  Reasoning:
    ✓ Agency has high trust profile
    Identified 1 risk signal(s):
      • account_maturity: New account (5 days old)
    DECISION: Approve booking - Low risk profile
    Consider increasing credit limit by 0.5%

[STEP 2] Execute Transaction
  ✓ Transaction confirmed: TXN_BUY_MERCHANT_001_...

[STEP 3] Update Trust Model
  ✓ Trust model updated
    - New trust score: 79.95/100
    - Credit increase: 0.5%
```

### Agency Status Dashboard
```
Agency Status: MERCHANT_001
Trust Score: 79.95/100
Risk Level: LOW

Dimension Scores:
  Financial Discipline:    68.50/100
    • On-time Ratio: 50.00%
    • Utilization: 0.00%
    • Outstanding: $0.00
  Behavioral Stability:    85.00/100
    • Velocity Spike: 2.00x
    • Cancellation Rate: 0.00%
    • Trend: increasing
  Operational Legitimacy: 72.50/100
    • Account Age: 5 days
    • Unique Geos: US-CA

Recent Bookings:
  ✓ BUY_MERCHANT_001_1: $10,000.00 (approve)
```

---

## 🔐 Risk Thresholds & Decisions

| Risk Score | Decision | Action |
|-----------|----------|--------|
| < 20 | APPROVE | Proceed with booking |
| 20-35 | APPROVE_WITH_MONITORING | Approve but flag for review |
| 35-50 | REDUCE_EXPOSURE | Cap at 50% of normal limit |
| 50-65 | ESCALATE | Manual review required |
| > 65 | RESTRICT | Block transaction, notify compliance |

---

## 📈 Trust Evolution Example

**Day 1:** Agency created
- Trust: 79.72/100
- Status: All factors neutral (baseline)

**Day 1:** $10,000 booking approved
- Risk: 12.45/100 (low)
- Trust: 79.95/100 (+0.23)
- Behavioral factors increase

**Day 2:** $5,000 payment processed
- Outstanding: $5,000 → $0
- Trust: 80.18/100 (+0.23)
- Financial discipline improves

**Day 3-32:** Time passes
- Account age: 0 → 30 days
- Operational legitimacy increases
- Trust: 85.00/100 (+4.82)
- Risk level: LOW → VERY LOW

---

## 🛠️ Configuration & Customization

### Trust Weights (in `long_term_trust_model.py`)
```python
composite_score = (
    financial_score * 0.40 +    # Can adjust
    behavioral_score * 0.35 +   # Can adjust
    operational_score * 0.25    # Can adjust
)
```

### Risk Thresholds (in `booking_risk_evaluator.py`)
```python
self.risk_thresholds = {
    'approve': 20,           # < 20
    'monitor': 35,           # 20-35
    'reduce': 50,            # 35-50
    'escalate': 65,          # 50-65
    'restrict': 100          # > 65
}
```

### Signal Severities (in `booking_risk_evaluator.py`)
- Velocity spike: Max 1.5x penalty
- Value deviation: Max 1.0 severity
- Device anomaly: 0.3 fixed severity
- Credit utilization: Max 1.0 severity
- Account maturity: Max 1.0 severity (new accounts)

---

## 📝 Database Location

- **Default Database:** `simulation.db` (SQLite)
- **Location:** `d:\tbo hackathon\simulation.db`
- **Auto-created:** On first agency creation
- **Persistent:** Survives across sessions

---

## 🎓 Use Cases

1. **Fraud Prevention**
   - Block high-risk bookings automatically
   - Detect velocity spikes and unusual patterns
   - Flag new accounts for verification

2. **Credit Risk Management**
   - Monitor payment discipline
   - Track outstanding amounts
   - Adjust credit limits dynamically

3. **Compliance & AML**
   - Verify document submission
   - Track business registration
   - Monitor verification status

4. **Customer Profiling**
   - Understand booking patterns
   - Track location diversity
   - Monitor account maturity

---

## 📞 Support & Extension

The system is designed for easy extension:
- Add new risk signals in `BookingRiskEvaluator`
- Add new trust factors in `LongTermTrustModel`
- Add new activities/incidents with `apply_positive_activity()` and `apply_incident()`
- Generate custom reports using `TrustManager.generate_risk_report()`

---

**Version:** 1.0  
**Last Updated:** March 1, 2026  
**Status:** Production Ready
