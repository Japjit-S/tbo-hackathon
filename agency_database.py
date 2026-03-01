"""
Agency Database - SQLite persistence for agencies and trust data
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
from long_term_trust_model import LongTermTrustModel


class AgencyDatabase:
    def __init__(self, db_path: str = "simulation.db"):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._initialize_db()

    def _initialize_db(self):
        """Create tables if they don't exist"""
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()

        # Agencies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agencies (
                agency_id TEXT PRIMARY KEY,
                created_at TEXT,
                updated_at TEXT,
                current_trust_score REAL,
                risk_level TEXT
            )
        """)

        # Financial factors
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_factors (
                agency_id TEXT PRIMARY KEY,
                on_time_payment_ratio REAL,
                credit_utilization_ratio REAL,
                outstanding_amount REAL,
                default_history INTEGER,
                chargeback_ratio REAL,
                FOREIGN KEY (agency_id) REFERENCES agencies(agency_id)
            )
        """)

        # Behavioral factors
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS behavioral_factors (
                agency_id TEXT PRIMARY KEY,
                booking_frequency REAL,
                velocity_spike_multiplier REAL,
                cancellation_ratio REAL,
                location_diversity INTEGER,
                booking_value_trend TEXT,
                FOREIGN KEY (agency_id) REFERENCES agencies(agency_id)
            )
        """)

        # Operational factors
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operational_factors (
                agency_id TEXT PRIMARY KEY,
                account_age_days INTEGER,
                unique_geos TEXT,
                document_verification INTEGER,
                registered_business INTEGER,
                support_contact_verified INTEGER,
                api_usage INTEGER,
                FOREIGN KEY (agency_id) REFERENCES agencies(agency_id)
            )
        """)

        # Trust snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trust_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agency_id TEXT,
                timestamp TEXT,
                financial_score REAL,
                behavioral_score REAL,
                operational_score REAL,
                composite_score REAL,
                notes TEXT,
                FOREIGN KEY (agency_id) REFERENCES agencies(agency_id)
            )
        """)

        # Transaction history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                agency_id TEXT,
                transaction_type TEXT,
                amount REAL,
                status TEXT,
                timestamp TEXT,
                notes TEXT,
                FOREIGN KEY (agency_id) REFERENCES agencies(agency_id)
            )
        """)

        # Risk profiles (monthly personalized thresholds)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agency_risk_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agency_id TEXT,
                month_number INTEGER,
                avg_booking_value REAL,
                normal_booking_frequency REAL,
                velocity_threshold REAL,
                signal_weights TEXT,
                created_at TEXT,
                FOREIGN KEY (agency_id) REFERENCES agencies(agency_id)
            )
        """)

        # Behavior profiles (for anomaly detection)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agency_behavior_profiles (
                agency_id TEXT PRIMARY KEY,
                avg_booking_amount REAL,
                std_dev_booking_amount REAL,
                min_booking_amount REAL,
                max_booking_amount REAL,
                booking_frequency_per_week REAL,
                known_geos TEXT,
                merchant_categories TEXT,
                typical_booking_hours TEXT,
                avg_payment_recovery_days REAL,
                booking_payment_ratio REAL,
                size_trend TEXT,
                transaction_count INTEGER,
                updated_at TEXT,
                FOREIGN KEY (agency_id) REFERENCES agencies(agency_id)
            )
        """)

        self.connection.commit()

    def save_agency(self, model: LongTermTrustModel) -> bool:
        """Save/update agency and all factors"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        now = datetime.now().isoformat()
        trust_score = model.get_composite_trust_score()

        # Determine risk level
        if trust_score >= 80:
            risk_level = "LOW"
        elif trust_score >= 60:
            risk_level = "MODERATE"
        elif trust_score >= 40:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        try:
            # Save agency
            cursor.execute("""
                INSERT OR REPLACE INTO agencies (agency_id, created_at, updated_at, current_trust_score, risk_level)
                VALUES (?, ?, ?, ?, ?)
            """, (model.agency_id, model.created_at.isoformat(), now, trust_score, risk_level))

            # Save financial factors
            cursor.execute("""
                INSERT OR REPLACE INTO financial_factors
                (agency_id, on_time_payment_ratio, credit_utilization_ratio, outstanding_amount, default_history, chargeback_ratio)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                model.agency_id,
                model.financial.on_time_payment_ratio,
                model.financial.credit_utilization_ratio,
                model.financial.outstanding_amount,
                model.financial.default_history,
                model.financial.chargeback_ratio
            ))

            # Save behavioral factors
            cursor.execute("""
                INSERT OR REPLACE INTO behavioral_factors
                (agency_id, booking_frequency, velocity_spike_multiplier, cancellation_ratio, location_diversity, booking_value_trend)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                model.agency_id,
                model.behavioral.booking_frequency,
                model.behavioral.velocity_spike_multiplier,
                model.behavioral.cancellation_ratio,
                model.behavioral.location_diversity,
                model.behavioral.booking_value_trend
            ))

            # Save operational factors
            cursor.execute("""
                INSERT OR REPLACE INTO operational_factors
                (agency_id, account_age_days, unique_geos, document_verification, registered_business, support_contact_verified, api_usage)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                model.agency_id,
                model.operational.account_age_days,
                json.dumps(model.operational.unique_geos),
                1 if model.operational.document_verification else 0,
                1 if model.operational.registered_business else 0,
                1 if model.operational.support_contact_verified else 0,
                model.operational.api_usage
            ))

            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error saving agency: {e}")
            return False

    def get_agency(self, agency_id: str) -> Optional[LongTermTrustModel]:
        """Retrieve agency and restore trust model"""
        if not self.connection:
            return None

        cursor = self.connection.cursor()
        
        try:
            cursor.execute("SELECT * FROM agencies WHERE agency_id = ?", (agency_id,))
            agency_row = cursor.fetchone()
            
            if not agency_row:
                return None

            # Create model
            model = LongTermTrustModel(agency_id)

            # Get financial factors
            cursor.execute("SELECT * FROM financial_factors WHERE agency_id = ?", (agency_id,))
            fin_row = cursor.fetchone()
            if fin_row:
                model.financial.on_time_payment_ratio = fin_row[1]
                model.financial.credit_utilization_ratio = fin_row[2]
                model.financial.outstanding_amount = fin_row[3]
                model.financial.default_history = fin_row[4]
                model.financial.chargeback_ratio = fin_row[5]

            # Get behavioral factors
            cursor.execute("SELECT * FROM behavioral_factors WHERE agency_id = ?", (agency_id,))
            beh_row = cursor.fetchone()
            if beh_row:
                model.behavioral.booking_frequency = beh_row[1]
                model.behavioral.velocity_spike_multiplier = beh_row[2]
                model.behavioral.cancellation_ratio = beh_row[3]
                model.behavioral.location_diversity = beh_row[4]
                model.behavioral.booking_value_trend = beh_row[5]

            # Get operational factors
            cursor.execute("SELECT * FROM operational_factors WHERE agency_id = ?", (agency_id,))
            op_row = cursor.fetchone()
            if op_row:
                model.operational.account_age_days = op_row[1]
                model.operational.unique_geos = json.loads(op_row[2]) if op_row[2] else ["US-CA"]
                model.operational.document_verification = bool(op_row[3])
                model.operational.registered_business = bool(op_row[4])
                model.operational.support_contact_verified = bool(op_row[5])
                model.operational.api_usage = op_row[6]

            return model
        except Exception as e:
            print(f"Error retrieving agency: {e}")
            return None

    def save_trust_snapshot(self, agency_id: str, model: LongTermTrustModel) -> bool:
        """Save trust snapshot for historical tracking"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO trust_snapshots
                (agency_id, timestamp, financial_score, behavioral_score, operational_score, composite_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                agency_id,
                datetime.now().isoformat(),
                model.financial.to_score(),
                model.behavioral.to_score(),
                model.operational.to_score(),
                model.get_composite_trust_score()
            ))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error saving snapshot: {e}")
            return False

    def get_agency_trust_history(self, agency_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get trust evolution over time"""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT timestamp, financial_score, behavioral_score, operational_score, composite_score
                FROM trust_snapshots
                WHERE agency_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (agency_id, limit))
            
            rows = cursor.fetchall()
            history = []
            for row in rows:
                history.append({
                    'timestamp': row[0],
                    'financial': row[1],
                    'behavioral': row[2],
                    'operational': row[3],
                    'composite': row[4]
                })
            return history
        except Exception as e:
            print(f"Error retrieving history: {e}")
            return []

    def save_transaction(self, transaction_id: str, agency_id: str, txn_type: str, amount: float, status: str, notes: str = "") -> bool:
        """Log transaction"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO transactions (transaction_id, agency_id, transaction_type, amount, status, timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (transaction_id, agency_id, txn_type, amount, status, datetime.now().isoformat(), notes))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error saving transaction: {e}")
            return False

    def get_agency_transactions(self, agency_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transactions for an agency"""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT transaction_id, transaction_type, amount, status, timestamp, notes
                FROM transactions
                WHERE agency_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (agency_id, limit))
            
            rows = cursor.fetchall()
            transactions = []
            for row in rows:
                transactions.append({
                    'id': row[0],
                    'type': row[1],
                    'amount': row[2],
                    'status': row[3],
                    'timestamp': row[4],
                    'notes': row[5]
                })
            return transactions
        except Exception as e:
            print(f"Error retrieving transactions: {e}")
            return []

    def get_agencies_by_risk_level(self, risk_level: str) -> List[str]:
        """Get all agencies at a specific risk level"""
        if not self.connection:
            return []

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT agency_id FROM agencies WHERE risk_level = ? ORDER BY current_trust_score DESC
            """, (risk_level,))
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error querying by risk level: {e}")
            return []

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

    def save_risk_profile(self, agency_id: str, month_number: int, profile_data: Dict[str, Any]) -> bool:
        """Save monthly risk profile for agency"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO agency_risk_profiles
                (agency_id, month_number, avg_booking_value, normal_booking_frequency, velocity_threshold, signal_weights, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                agency_id,
                month_number,
                profile_data.get('avg_booking_value', 0),
                profile_data.get('normal_booking_frequency', 0),
                profile_data.get('velocity_threshold', 1.5),
                json.dumps(profile_data.get('signal_weights', {})),
                datetime.now().isoformat()
            ))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error saving risk profile: {e}")
            return False

    def get_risk_profile(self, agency_id: str, month_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve risk profile for agency at specific month"""
        if not self.connection:
            return None

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT avg_booking_value, normal_booking_frequency, velocity_threshold, signal_weights
                FROM agency_risk_profiles
                WHERE agency_id = ? AND month_number = ?
            """, (agency_id, month_number))
            
            row = cursor.fetchone()
            if not row:
                return None

            return {
                'avg_booking_value': row[0],
                'normal_booking_frequency': row[1],
                'velocity_threshold': row[2],
                'signal_weights': json.loads(row[3]) if row[3] else {}
            }
        except Exception as e:
            print(f"Error retrieving risk profile: {e}")
            return None

    def save_behavior_profile(self, agency_id: str, behavior_data: Dict[str, Any]) -> bool:
        """Save agency behavior profile for anomaly detection"""
        if not self.connection:
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO agency_behavior_profiles
                (agency_id, avg_booking_amount, std_dev_booking_amount, min_booking_amount, max_booking_amount,
                 booking_frequency_per_week, known_geos, merchant_categories, typical_booking_hours,
                 avg_payment_recovery_days, booking_payment_ratio, size_trend, transaction_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agency_id,
                behavior_data.get('avg_booking_amount', 0),
                behavior_data.get('std_dev_booking_amount', 0),
                behavior_data.get('min_booking_amount', 0),
                behavior_data.get('max_booking_amount', 0),
                behavior_data.get('booking_frequency_per_week', 0),
                json.dumps(behavior_data.get('known_geos', [])),
                json.dumps(behavior_data.get('merchant_categories', [])),
                json.dumps(behavior_data.get('typical_booking_hours', [])),
                behavior_data.get('avg_payment_recovery_days', 0),
                behavior_data.get('booking_payment_ratio', 0.5),
                behavior_data.get('size_trend', 'stable'),
                behavior_data.get('transaction_count', 0),
                datetime.now().isoformat()
            ))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error saving behavior profile: {e}")
            return False

    def get_behavior_profile(self, agency_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve behavior profile for agency"""
        if not self.connection:
            return None

        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT avg_booking_amount, std_dev_booking_amount, min_booking_amount, max_booking_amount,
                       booking_frequency_per_week, known_geos, merchant_categories, typical_booking_hours,
                       avg_payment_recovery_days, booking_payment_ratio, size_trend, transaction_count
                FROM agency_behavior_profiles
                WHERE agency_id = ?
            """, (agency_id,))
            
            row = cursor.fetchone()
            if not row:
                return None

            return {
                'avg_booking_amount': row[0],
                'std_dev_booking_amount': row[1],
                'min_booking_amount': row[2],
                'max_booking_amount': row[3],
                'booking_frequency_per_week': row[4],
                'known_geos': json.loads(row[5]) if row[5] else [],
                'merchant_categories': json.loads(row[6]) if row[6] else [],
                'typical_booking_hours': json.loads(row[7]) if row[7] else [],
                'avg_payment_recovery_days': row[8],
                'booking_payment_ratio': row[9],
                'size_trend': row[10],
                'transaction_count': row[11]
            }
        except Exception as e:
            print(f"Error retrieving behavior profile: {e}")
            return None
