"""
Interactive Transaction Simulator
Manual testing with buy/sell transactions, behavioral learning, and monthly adaptation
"""

from trust_manager import TrustManager
from transaction_processor import TransactionProcessor
from booking_risk_evaluator import BookingRequest
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple


class TransactionSimulator:
    """Interactive simulator for testing transactions with behavioral learning"""

    def __init__(self):
        self.trust_manager = TrustManager("simulation.db")
        self.processor = TransactionProcessor(self.trust_manager)
        self.current_date = datetime.now()
        self.agencies: Dict[str, Dict[str, Any]] = {}  # agency_id -> {created_date, txn_count, created_at_day}
        self.baseline_date = self.current_date

    def create_agency(self, agency_id: str) -> None:
        """Create new agency with baseline factors"""
        model = self.trust_manager.create_agency(agency_id)
        self.agencies[agency_id] = {
            "created_at_day": 0,
            "txn_count": 0,
            "account_age_days": 0,
            "evaluation_mode": "BASELINE"
        }
        print(f"\n✓ Agency created with baseline trust: {model.get_composite_trust_score():.2f}/100")
        print(f"  Baseline factors initialized (neutral)")
        print(f"  Monthly Credit Limit: $5,000.00")
        print(f"  Evaluation Mode: BASELINE (Month 1, Days 0-29)")

    def process_buy_transaction(self, agency_id: str, amount: float, location: str, notes: str = "") -> None:
        """Process booking transaction (buy)"""
        from booking_risk_evaluator import BookingRequest
        
        # Calculate days since creation
        days_since_creation = self.agencies[agency_id]["account_age_days"]
        evaluation_mode = "BASELINE" if days_since_creation < 30 else "PERSONALIZED"
        self.agencies[agency_id]["evaluation_mode"] = evaluation_mode
        
        print(f"\n{'─'*80}\nBUY Transaction: BUY_{agency_id}_{len(self.processor.transaction_log) + 1}\n{'─'*80}")
        print(f"Amount: ${amount:,.2f}")
        print(f"Location: {location}")
        print(f"Days Since Creation: {days_since_creation}")
        if notes:
            print(f"Notes: {notes}")

        record = self.processor.process_booking(agency_id, amount, location, notes)

        print(f"\n{'='*80}\nProcessing Booking: {record['booking_id']}\n{'='*80}")

        print(f"\n[STEP 1] Real-Time Risk Evaluation")
        print(f"  Evaluation Mode: {evaluation_mode} - {'Using generic thresholds (Month 1)' if evaluation_mode == 'BASELINE' else 'Using learned behavior patterns (Month 2+)'}")
        print(f"  Agency: {agency_id}")
        print(f"  Value: ${amount:,.2f}")
        print(f"  Location: {location}")
        print(f"  Device: DEV_web_001")
        
        print(f"\n  Monthly Credit Limit: ${record.get('monthly_credit_limit', 5000):,.2f}")
        print(f"  Current Outstanding: ${record.get('current_outstanding', 0):,.2f}")
        print(f"  Exposure Ratio: {record.get('exposure_ratio', 0)*100:.1f}%")
        
        print(f"\n  Risk Analysis:")
        print(f"    Base Anomaly Score: {record.get('base_anomaly_score', 0):.2f}/100")
        print(f"    Trust Context Score: {record['trust_context']:.2f}/100")
        print(f"    Risk Score: {record['risk_score']:.2f}/100")
        print(f"    Decision: {record['decision'].upper()}")
        print(f"    Confidence: {95.0 if record['decision'] == 'approve' else 80.0}%")
        
        print(f"\n  Risk Signals (Traditional Fraud Indicators):")
        
        # Get detailed assessment for signals
        request = BookingRequest(
            agency_id=agency_id,
            booking_id=record['booking_id'],
            amount=amount,
            location=location,
            device_id='DEV_web_001',
            timestamp=datetime.now()
        )
        
        agency_model = self.trust_manager.get_agency(agency_id)
        signals = self.processor.evaluator._detect_risk_signals(request, agency_model)
        
        if signals:
            for signal in signals:
                severity_pct = signal.severity * 100
                print(f"    • {signal.signal_type} ({severity_pct:.0f}%): {signal.description}")
        else:
            print(f"    • None detected")
        
        # Display behavioral anomalies with learning status
        print(f"\n  Behavioral Anomalies (Pattern-Based Detection):")
        
        # Load and check behavior profile for learning status
        behavior_profile = self.trust_manager.db.get_behavior_profile(agency_id)
        txn_count = behavior_profile["transaction_count"] if behavior_profile else 0
        
        if txn_count < 5:
            print(f"    • Status: LEARNING (Need {5-txn_count} more transaction(s) to activate)")
            print(f"      Current transactions: {txn_count}/5")
        else:
            print(f"    • Status: ACTIVE (Learned from {txn_count} transactions)")
            
            if record.get('behavioral_anomalies'):
                for anomaly_type, severity, description in record['behavioral_anomalies']:
                    severity_pct = severity * 100
                    print(f"    • {anomaly_type} ({severity_pct:.0f}%): {description}")
            else:
                print(f"    • None - matches learned patterns")

        print(f"\n  Reasoning:")
        print(f"{record['reasoning']}")

        if record['transaction_id']:
            print(f"\n[STEP 2] Execute Transaction")
            print(f"  ✓ Transaction confirmed: {record['transaction_id']}")
            print(f"    Status: {record.get('status', 'PROCESSED')}")
            
            print(f"\n[STEP 3] Update Trust Model")
            new_trust = self.trust_manager.get_trust_score(agency_id) or 0
            print(f"  ✓ Trust model updated")
            print(f"    - New trust score: {new_trust:.2f}/100")
            print(f"    - Credit increase: +{record.get('credit_increase_pct', 0):.2f}%")
            print(f"    - New credit limit: ${record.get('new_credit_limit', 5000):,.2f}")
            
            # Update simulation tracking
            self.agencies[agency_id]["txn_count"] += 1
        else:
            print(f"\n[STEP 2] Transaction BLOCKED")
            print(f"  ✗ Risk too high: {record.get('decision', 'RESTRICT').upper()}")
            print(f"  No trust update")

    def process_sell_transaction(self, agency_id: str, amount: float, notes: str = "") -> None:
        """Process payment transaction (sell)"""
        print(f"\n{'─'*70}\nSELL Transaction (Payment): {agency_id}\n{'─'*70}")
        print(f"Amount: ${amount:,.2f}")
        print(f"Notes: {notes}")

        record = self.processor.process_payment(agency_id, amount, notes)

        if 'error' not in record:
            print(f"\n{'='*70}\nProcessing Payment\n{'='*70}")
            print(f"  Agency: {agency_id}")
            print(f"  Amount: ${amount:,.2f}")
            print(f"\n  ✓ Payment processed successfully")
            print(f"    - Outstanding reduced: ${record['old_outstanding']:.2f} → ${record['new_outstanding']:.2f}")
            print(f"    - Old trust: {record['old_trust']:.2f}/100")
            print(f"    - New trust: {record['new_trust']:.2f}/100")
            print(f"    - Trust improvement: +{record['trust_improvement']:.2f}")

    def show_agency_status(self, agency_id: str) -> None:
        """Display comprehensive agency status"""
        status = self.trust_manager.get_agency_status(agency_id)
        if not status:
            print(f"✗ Agency {agency_id} not found")
            return

        print(f"\n{'='*80}\nAgency Status: {agency_id}\n{'='*80}\n")
        
        # Get agency model for credit limit and exposure
        agency_model = self.trust_manager.get_agency(agency_id)
        monthly_limit = agency_model.get_monthly_credit_limit() if agency_model else 5000
        exposure = agency_model.get_exposure_ratio() if agency_model else 0
        
        # Determine evaluation mode based on account age
        days_since_creation = self.agencies[agency_id]["account_age_days"] if agency_id in self.agencies else 0
        eval_mode = "BASELINE (Month 1)" if days_since_creation < 30 else "PERSONALIZED (Month 2+)"
        
        print(f"Evaluation Mode: {eval_mode}")
        print(f"Account Age: {days_since_creation} days")
        print(f"Total Bookings: {self.agencies[agency_id]['txn_count'] if agency_id in self.agencies else 0}\n")
        
        print(f"Trust Score: {status['trust_score']:.2f}/100")
        
        if status['trust_score'] >= 80:
            risk = "LOW RISK ✓"
        elif status['trust_score'] >= 60:
            risk = "MODERATE RISK"
        elif status['trust_score'] >= 40:
            risk = "HIGH RISK ⚠"
        else:
            risk = "CRITICAL RISK ✗"
        print(f"Risk Level: {risk}\n")

        print(f"Credit Limits:")
        print(f"  Monthly Credit Limit: ${monthly_limit:,.2f}")
        print(f"  Current Outstanding: ${status['financial']['outstanding']:,.2f}")
        print(f"  Available Credit: ${max(0, monthly_limit - status['financial']['outstanding']):,.2f}")
        print(f"  Exposure Ratio: {exposure*100:.1f}%")
        
        if exposure > 0.8:
            print(f"    ⚠ CRITICAL: Using {exposure*100:.1f}% of available credit\n")
        else:
            print()

        print(f"Dimension Scores:")
        print(f"  Financial Discipline: {status['financial_score']:.2f}/100")
        print(f"    • On-time Ratio: {status['financial']['on_time_ratio']:.2f}%")
        print(f"    • Credit Utilization: {status['financial']['utilization']:.2f}%")
        print(f"    • Default Rate: {status['financial'].get('defaults', 0)}%")
        print(f"    • Outstanding Balance: ${status['financial']['outstanding']:,.2f}")
        
        print(f"\n  Behavioral Stability: {status['behavioral_score']:.2f}/100")
        print(f"    • Booking Velocity: {status['behavioral']['velocity']:.2f}x baseline")
        print(f"    • Cancellation Rate: {status['behavioral']['cancellation']:.2f}%")
        print(f"    • Trend: {status['behavioral']['trend']}")
        print(f"    • Location Diversity: {', '.join(status['operational']['geos']) if status['operational']['geos'] else 'Single region'}")
        
        print(f"\n  Operational Legitimacy: {status['operational_score']:.2f}/100")
        print(f"    • Account Age: {status['operational']['age_days']} days")
        print(f"    • Known Locations: {', '.join(status['operational']['geos']) if status['operational']['geos'] else 'None'}")
        
        # Show behavior profile learning status
        behavior_profile = self.trust_manager.db.get_behavior_profile(agency_id)
        print(f"\n  Behavioral Learning:")
        if behavior_profile:
            txn_count = behavior_profile["transaction_count"]
            print(f"    • Status: {'ACTIVE ✓' if txn_count >= 5 else f'LEARNING ({txn_count}/5 transactions)'}")
            if txn_count >= 5:
                print(f"    • Avg Booking Amount: ${behavior_profile.get('avg_booking_amount', 0):,.2f}")
                print(f"    • Amount Std Dev: ${behavior_profile.get('std_dev', 0):,.2f}")
                print(f"    • Typical Booking Hours: {behavior_profile.get('merchant_categories', ['TRAVEL'])[0]}")
        else:
            print(f"    • Status: LEARNING (0/5 transactions)\n")

        # Show recent bookings with decisions
        txns = self.processor.get_agency_transactions(agency_id)
        if txns:
            print(f"\nRecent Transactions:")
            for txn in txns[-5:]:
                if txn.get('transaction_type') == 'BOOKING':
                    decision = txn.get('decision', 'UNKNOWN').upper()
                    symbol = "✓" if decision == "APPROVE" else "⚠" if decision in ["APPROVE_WITH_MONITORING", "REDUCE_EXPOSURE"] else "✗"
                    print(f"  {symbol} {txn.get('transaction_id', 'UNKNOWN')}: ${txn['amount']:,.2f} - {decision}")
                else:
                    print(f"  💳 {txn.get('transaction_id', 'UNKNOWN')}: ${txn['amount']:,.2f} - PAYMENT")

    def advance_date(self, days: int = 1) -> None:
        """Simulate time passing with mode switching detection"""
        old_date = self.current_date
        self.current_date += timedelta(days=days)
        
        # Update account ages and detect mode switches
        mode_switches = []
        for agency_id in self.agencies:
            old_age = self.agencies[agency_id]["account_age_days"]
            self.agencies[agency_id]["account_age_days"] += days
            new_age = self.agencies[agency_id]["account_age_days"]
            
            # Check for baseline -> personalized switch at day 30
            if old_age < 30 and new_age >= 30:
                mode_switches.append(agency_id)
            
            agency = self.trust_manager.get_agency(agency_id)
            if agency:
                agency.operational.account_age_days += days
                self.trust_manager.db.save_agency(agency)
        
        print(f"\n⏰ Time Advanced")
        print(f"  Old Date: {old_date.strftime('%Y-%m-%d')}")
        print(f"  New Date: {self.current_date.strftime('%Y-%m-%d')}")
        print(f"  Days: +{days}")
        
        if mode_switches:
            print(f"\n  ⚡ Evaluation Mode Switches (BASELINE → PERSONALIZED):")
            for agency_id in mode_switches:
                print(f"    • {agency_id}: Switched at Day 30")
                print(f"      - Behavior profile activated")
                print(f"      - Personalized anomaly detection now active")
                print(f"      - Thresholds adapted to learned patterns")

    def show_summary(self) -> None:
        """Show detailed system summary"""
        print(f"\n{'='*80}\nSystem Summary\n{'='*80}\n")
        print(f"Current Date: {self.current_date.strftime('%Y-%m-%d')}")
        print(f"Active Agencies: {len(self.agencies)}")
        
        total_txns = len(self.processor.transaction_log)
        bookings = len([t for t in self.processor.transaction_log if t.get('transaction_type') == 'BOOKING'])
        payments = len([t for t in self.processor.transaction_log if t.get('transaction_type') == 'PAYMENT'])
        print(f"Total Transactions: {total_txns} (Bookings: {bookings}, Payments: {payments})\n")

        print(f"Agency Summary:")
        print(f"{'─'*80}")
        print(f"{'Agency ID':<20} {'Trust':<12} {'Status':<15} {'Bookings':<12} {'Mode':<20}")
        print(f"{'─'*80}")
        
        for agency_id in self.agencies:
            trust = self.trust_manager.get_trust_score(agency_id) or 0
            
            # Determine risk status
            if trust >= 80:
                status = "LOW RISK ✓"
            elif trust >= 60:
                status = "MODERATE"
            elif trust >= 40:
                status = "HIGH RISK ⚠"
            else:
                status = "CRITICAL ✗"
            
            bookings_count = self.agencies[agency_id]['txn_count']
            
            # Determine mode
            days = self.agencies[agency_id]['account_age_days']
            mode = "BASELINE (0-30d)" if days < 30 else "PERSONALIZED (30+d)"
            
            print(f"{agency_id:<20} {trust:>6.2f}/100   {status:<15} {bookings_count:<12} {mode:<20}")
        
        print(f"{'─'*80}\n")
        
        # Show transaction breakdown
        if bookings > 0:
            approved = len([t for t in self.processor.transaction_log 
                           if t.get('transaction_type') == 'BOOKING' and t.get('decision') == 'approve'])
            approval_rate = (approved / bookings) * 100
            print(f"Transaction Statistics:")
            print(f"  Booking Approval Rate: {approval_rate:.1f}% ({approved}/{bookings})")
            
            # Total value booked
            total_booked = sum([t.get('amount', 0) for t in self.processor.transaction_log 
                               if t.get('transaction_type') == 'BOOKING'])
            print(f"  Total Booking Value: ${total_booked:,.2f}")
            
            # Total payments
            total_paid = sum([t.get('amount', 0) for t in self.processor.transaction_log 
                             if t.get('transaction_type') == 'PAYMENT'])
            print(f"  Total Payments: ${total_paid:,.2f}")
            
            if total_booked > 0:
                collection_rate = (total_paid / total_booked) * 100
                print(f"  Collection Rate: {collection_rate:.1f}%")

    def run_scenario(self, scenario_name: str) -> None:
        """Run predefined test scenarios"""
        if scenario_name == "conservative":
            self._scenario_conservative()
        elif scenario_name == "aggressive":
            self._scenario_aggressive()
        elif scenario_name == "fraud":
            self._scenario_fraud_detection()
        else:
            print(f"✗ Unknown scenario: {scenario_name}")

    def _scenario_conservative(self) -> None:
        """Scenario: Conservative bookings with steady growth"""
        print(f"\n{'='*80}\nRunning Scenario: CONSERVATIVE (Steady Growth)\n{'='*80}\n")
        
        agency_id = "CONSERVATIVE_AGENCY"
        print(f"Creating agency: {agency_id}")
        self.create_agency(agency_id)
        
        # Day 1-5: Small consistent bookings
        for day in range(5):
            self.advance_date(1)
            amount = 3500 + (day * 100)  # Slight growth
            print(f"\n→ Day {day+1} Booking")
            self.process_buy_transaction(agency_id, amount, "US-CA", f"Booking #{day+1}")
        
        # Day 10: Show status
        self.advance_date(5)
        print(f"\n→ Day 10 Status Check")
        self.show_agency_status(agency_id)
        
        # Day 15-20: More bookings
        for day in range(5):
            self.advance_date(1)
            amount = 3800 + (day * 50)
            print(f"\n→ Day {14+day} Booking")
            self.process_buy_transaction(agency_id, amount, "US-CA", f"Booking #{day+6}")
        
        # Day 25: Payment
        self.advance_date(5)
        print(f"\n→ Day 25 Payment")
        self.process_sell_transaction(agency_id, 10000, "Partial payment")
        
        # Day 30: Final day of baseline, show status
        self.advance_date(5)
        print(f"\n→ Day 30 Status (End of BASELINE month)")
        self.show_agency_status(agency_id)
        
        # Day 31: Now in personalized mode
        self.advance_date(1)
        print(f"\n→ Day 31 Booking (Now in PERSONALIZED mode)")
        self.process_buy_transaction(agency_id, 3700, "US-CA", "Normal booking")

    def _scenario_aggressive(self) -> None:
        """Scenario: Fraud-like aggressive bookings"""
        print(f"\n{'='*80}\nRunning Scenario: AGGRESSIVE (Anomaly Detection)\n{'='*80}\n")
        
        agency_id = "AGGRESSIVE_AGENCY"
        print(f"Creating agency: {agency_id}")
        self.create_agency(agency_id)
        
        # Day 1: Small initial booking
        print(f"\n→ Day 1 Initial Booking")
        self.process_buy_transaction(agency_id, 2000, "US-CA", "Initial booking")
        
        self.advance_date(1)
        print(f"\n→ Day 2 Second Booking")
        self.process_buy_transaction(agency_id, 2500, "US-NY", "Second booking")
        
        self.advance_date(1)
        print(f"\n→ Day 3 Suspicious Booking")
        self.process_buy_transaction(agency_id, 35000, "EU-UK", "⚠ Large unusual booking")
        
        # Show status and explain why it was flagged
        print(f"\n→ Day 3 Status Check")
        self.show_agency_status(agency_id)

    def _scenario_fraud_detection(self) -> None:
        """Scenario: Full fraud cycle - learning then fraudulent transaction"""
        print(f"\n{'='*80}\nRunning Scenario: FRAUD DETECTION (Pattern-Based)\n{'='*80}\n")
        
        agency_id = "FRAUD_TEST_AGENCY"
        print(f"Creating agency: {agency_id}")
        self.create_agency(agency_id)
        
        # Build 5+ transactions to activate learning
        print(f"\n[Phase 1] Building Behavior Profile (5+ transactions needed)")
        for i in range(5):
            self.advance_date(1)
            amount = 3500 + (i * 100)
            hour = (9 + i) % 24
            print(f"\n→ Day {i+1} Transaction #{i+1}")
            self.process_buy_transaction(agency_id, amount, "US-CA", f"Normal booking #{i+1}")
        
        # Show status with behavior profile active
        self.advance_date(1)
        print(f"\n→ Day 6 Status (Behavior Profile ACTIVE)")
        self.show_agency_status(agency_id)
        
        # Day 30: Switch to personalized
        self.advance_date(24)
        print(f"\n[Phase 2] Switching to PERSONALIZED Evaluation (Day 30)")
        self.advance_date(1)
        
        # Normal transaction should pass
        print(f"\n→ Day 31 Normal Transaction (should APPROVE)")
        self.process_buy_transaction(agency_id, 3600, "US-CA", "Normal pattern")
        
        # Fraudulent transaction
        print(f"\n→ Day 31 Fraudulent Transaction (should RESTRICT)")
        self.process_buy_transaction(agency_id, 25000, "CN-SH", "⚠ Large amount + new location + odd hours")


def interactive_menu():
    """Interactive menu for simulator"""
    simulator = TransactionSimulator()

    print("\n" + "="*80)
    print("  ADAPTIVE TRUST & CREDIT INTELLIGENCE ENGINE")
    print("  Interactive Fraud Prevention Simulator")
    print("="*80)
    print("\nFEATURES:")
    print("  ✓ 3-Dimensional Trust Model (Financial, Behavioral, Operational)")
    print("  ✓ Dynamic Monthly Credit Limits ($5K-$40K based on trust)")
    print("  ✓ Monthly Adaptive Evaluation (BASELINE Month 1, PERSONALIZED Month 2+)")
    print("  ✓ Behavioral Anomaly Detection (5 types with pattern learning)")
    print("  ✓ Real-time Risk Assessment with multiple signal detection")
    print("  ✓ Complete transaction history and profile persistence")

    while True:
        print(f"\n{'─'*80}")
        print("MAIN MENU:")
        print("  1. Create new agency")
        print("  2. Process BUY transaction (booking)")
        print("  3. Process SELL transaction (payment)")
        print("  4. View agency status")
        print("  5. Advance date (simulate time)")
        print("  6. Run test scenario")
        print("  7. Show system summary")
        print("  8. Exit")
        print(f"{'─'*80}")

        choice = input("\nSelect option (1-8): ").strip()

        if choice == '1':
            agency_id = input("Agency ID (e.g., AGENCY_001): ").strip()
            if agency_id:
                print(f"\n{'='*80}\nCreating Agency: {agency_id}\n{'='*80}")
                simulator.create_agency(agency_id)

        elif choice == '2':
            agency_id = input("Agency ID: ").strip()
            try:
                amount = float(input("Booking amount ($): "))
                location = input("Location (default US-CA): ").strip() or "US-CA"
                notes = input("Notes (optional): ").strip()
                simulator.process_buy_transaction(agency_id, amount, location, notes)
            except ValueError:
                print("✗ Invalid amount")

        elif choice == '3':
            agency_id = input("Agency ID: ").strip()
            try:
                amount = float(input("Payment amount ($): "))
                notes = input("Notes (optional): ").strip()
                simulator.process_sell_transaction(agency_id, amount, notes)
            except ValueError:
                print("✗ Invalid amount")

        elif choice == '4':
            agency_id = input("Agency ID: ").strip()
            if agency_id:
                simulator.show_agency_status(agency_id)

        elif choice == '5':
            try:
                days = int(input("Days to advance (default 1): ") or "1")
                simulator.advance_date(days)
            except ValueError:
                print("✗ Invalid number")

        elif choice == '6':
            print("\nAvailable Scenarios:")
            print("  1. conservative - Steady growth with small bookings")
            print("  2. aggressive - Large suspicious bookings early")
            print("  3. fraud - Full cycle from learning to fraud detection")
            
            scenario_choice = input("\nSelect scenario (1-3) or 'q' to cancel: ").strip()
            
            if scenario_choice == '1':
                simulator.run_scenario("conservative")
                simulator.show_summary()
            elif scenario_choice == '2':
                simulator.run_scenario("aggressive")
            elif scenario_choice == '3':
                simulator.run_scenario("fraud")
            elif scenario_choice != 'q':
                print("✗ Invalid scenario")

        elif choice == '7':
            simulator.show_summary()

        elif choice == '8':
            print("\n✓ Exiting simulator")
            simulator.trust_manager.close()
            break

        else:
            print("✗ Invalid option")


if __name__ == "__main__":
    interactive_menu()
