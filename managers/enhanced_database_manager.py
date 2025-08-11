"""
Enhanced Database Manager with Multi-Database Support
Updated: 2025-08-11 11:48:05 UTC by rasiharunart1
"""

import sqlite3
import json
import csv
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from abc import ABC, abstractmethod

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

from config.advanced_config import settings_manager, DATA_DIR, EXPORTS_DIR

class DatabaseInterface(ABC):
    """Abstract base class for database implementations"""
    
    @abstractmethod
    def connect(self) -> bool:
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: tuple = None) -> Any:
        pass
    
    @abstractmethod
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        pass
    
    @abstractmethod
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def create_tables(self) -> bool:
        pass

class SQLiteDatabase(DatabaseInterface):
    """SQLite database implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        self.db_path = Path(config['file_path'])
    
    def connect(self) -> bool:
        try:
            self.db_path.parent.mkdir(exist_ok=True)
            self.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self.connection.row_factory = sqlite3.Row
            return True
        except Exception as e:
            logging.error(f"SQLite connection error: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        try:
            cursor = self.connection.cursor()
            if params:
                result = cursor.execute(query, params)
            else:
                result = cursor.execute(query)
            self.connection.commit()
            return result
        except Exception as e:
            logging.error(f"SQLite query error: {e}")
            self.connection.rollback()
            raise
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"SQLite fetch error: {e}")
            return []
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"SQLite fetch one error: {e}")
            return None
    
    def create_tables(self) -> bool:
        try:
            # Enhanced schema with more detailed tracking
            tables = [
                '''CREATE TABLE IF NOT EXISTS detection_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    total_detections INTEGER DEFAULT 0,
                    model_used TEXT,
                    confidence_threshold REAL,
                    capture_region TEXT,
                    counting_lines TEXT,
                    notes TEXT,
                    created_by TEXT DEFAULT 'rasiharunart1'
                )''',
                
                '''CREATE TABLE IF NOT EXISTS vehicle_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    vehicle_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    bbox_x1 INTEGER,
                    bbox_y1 INTEGER,
                    bbox_x2 INTEGER,
                    bbox_y2 INTEGER,
                    track_id INTEGER,
                    line_crossed TEXT,
                    speed_estimate REAL,
                    FOREIGN KEY (session_id) REFERENCES detection_sessions (id)
                )''',
                
                '''CREATE TABLE IF NOT EXISTS traffic_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    vehicle_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    time_period TEXT,
                    FOREIGN KEY (session_id) REFERENCES detection_sessions (id)
                )''',
                
                '''CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    module TEXT,
                    message TEXT NOT NULL,
                    details TEXT
                )''',
                
                '''CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fps REAL,
                    detection_time REAL,
                    memory_usage REAL,
                    cpu_usage REAL,
                    gpu_usage REAL,
                    active_tracks INTEGER
                )'''
            ]
            
            for table_sql in tables:
                self.execute_query(table_sql)
            
            # Create indexes for better performance
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON vehicle_detections(timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_detections_session ON vehicle_detections(session_id)',
                'CREATE INDEX IF NOT EXISTS idx_detections_type ON vehicle_detections(vehicle_type)',
                'CREATE INDEX IF NOT EXISTS idx_statistics_session ON traffic_statistics(session_id)',
                'CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics(timestamp)'
            ]
            
            for index_sql in indexes:
                self.execute_query(index_sql)
            
            return True
            
        except Exception as e:
            logging.error(f"Error creating SQLite tables: {e}")
            return False

class MySQLDatabase(DatabaseInterface):
    """MySQL database implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    def connect(self) -> bool:
        if not MYSQL_AVAILABLE:
            logging.error("MySQL connector not available")
            return False
        
        try:
            self.connection = mysql.connector.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['username'],
                password=self.config['password'],
                autocommit=True
            )
            return True
        except Exception as e:
            logging.error(f"MySQL connection error: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logging.error(f"MySQL query error: {e}")
            raise
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        try:
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            logging.error(f"MySQL fetch error: {e}")
            return []
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        try:
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            return result
        except Exception as e:
            logging.error(f"MySQL fetch one error: {e}")
            return None
    
    def create_tables(self) -> bool:
        # Similar to SQLite but with MySQL syntax
        try:
            tables = [
                '''CREATE TABLE IF NOT EXISTS detection_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_name VARCHAR(255) NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP NULL,
                    total_detections INT DEFAULT 0,
                    model_used VARCHAR(100),
                    confidence_threshold DECIMAL(3,2),
                    capture_region TEXT,
                    counting_lines TEXT,
                    notes TEXT,
                    created_by VARCHAR(100) DEFAULT 'rasiharunart1'
                )''',
                # Add other tables with MySQL syntax...
            ]
            
            for table_sql in tables:
                self.execute_query(table_sql)
            return True
            
        except Exception as e:
            logging.error(f"Error creating MySQL tables: {e}")
            return False

class PostgreSQLDatabase(DatabaseInterface):
    """PostgreSQL database implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    def connect(self) -> bool:
        if not POSTGRESQL_AVAILABLE:
            logging.error("PostgreSQL connector not available")
            return False
        
        try:
            self.connection = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['username'],
                password=self.config['password']
            )
            self.connection.autocommit = True
            return True
        except Exception as e:
            logging.error(f"PostgreSQL connection error: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            try:
                result = cursor.fetchall()
            except:
                result = None
            cursor.close()
            return result
        except Exception as e:
            logging.error(f"PostgreSQL query error: {e}")
            raise
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict]:
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            return result
        except Exception as e:
            logging.error(f"PostgreSQL fetch error: {e}")
            return []
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"PostgreSQL fetch one error: {e}")
            return None
    
    def create_tables(self) -> bool:
        # PostgreSQL specific table creation
        try:
            tables = [
                '''CREATE TABLE IF NOT EXISTS detection_sessions (
                    id SERIAL PRIMARY KEY,
                    session_name VARCHAR(255) NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    total_detections INTEGER DEFAULT 0,
                    model_used VARCHAR(100),
                    confidence_threshold DECIMAL(3,2),
                    capture_region TEXT,
                    counting_lines JSONB,
                    notes TEXT,
                    created_by VARCHAR(100) DEFAULT 'rasiharunart1'
                )''',
                # Add other tables with PostgreSQL syntax...
            ]
            
            for table_sql in tables:
                self.execute_query(table_sql)
            return True
            
        except Exception as e:
            logging.error(f"Error creating PostgreSQL tables: {e}")
            return False

class EnhancedDatabaseManager:
    """Enhanced database manager with multi-database support"""
    
    def __init__(self):
        self.current_db: Optional[DatabaseInterface] = None
        self.current_session_id: Optional[int] = None
        self.connection_status = False
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for database operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def connect_database(self, db_type: str, config: Dict[str, Any]) -> bool:
        """Connect to specified database type"""
        try:
            if self.current_db:
                self.current_db.disconnect()
            
            if db_type == 'sqlite':
                self.current_db = SQLiteDatabase(config)
            elif db_type == 'mysql':
                self.current_db = MySQLDatabase(config)
            elif db_type == 'postgresql':
                self.current_db = PostgreSQLDatabase(config)
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
            
            if self.current_db.connect():
                self.connection_status = True
                self.current_db.create_tables()
                logging.info(f"Connected to {db_type} database successfully")
                return True
            else:
                self.connection_status = False
                return False
                
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            self.connection_status = False
            return False
    
    def test_connection(self, db_type: str, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Test database connection without setting as current"""
        try:
            if db_type == 'sqlite':
                test_db = SQLiteDatabase(config)
            elif db_type == 'mysql':
                if not MYSQL_AVAILABLE:
                    return False, "MySQL connector not installed"
                test_db = MySQLDatabase(config)
            elif db_type == 'postgresql':
                if not POSTGRESQL_AVAILABLE:
                    return False, "PostgreSQL connector not installed"
                test_db = PostgreSQLDatabase(config)
            else:
                return False, f"Unsupported database type: {db_type}"
            
            if test_db.connect():
                test_db.disconnect()
                return True, "Connection successful"
            else:
                return False, "Connection failed"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def start_session(self, session_name: str, model_used: str, 
                     confidence_threshold: float, capture_region: str,
                     counting_lines: str, notes: str = "") -> bool:
        """Start a new detection session"""
        if not self.current_db or not self.connection_status:
            return False
        
        try:
            query = '''INSERT INTO detection_sessions 
                      (session_name, model_used, confidence_threshold, 
                       capture_region, counting_lines, notes)
                      VALUES (?, ?, ?, ?, ?, ?)'''
            
            result = self.current_db.execute_query(
                query, 
                (session_name, model_used, confidence_threshold, 
                 capture_region, counting_lines, notes)
            )
            
            # Get the session ID
            session_query = "SELECT last_insert_rowid() as id"
            if isinstance(self.current_db, MySQLDatabase):
                session_query = "SELECT LAST_INSERT_ID() as id"
            elif isinstance(self.current_db, PostgreSQLDatabase):
                session_query = "SELECT currval('detection_sessions_id_seq') as id"
            
            session_result = self.current_db.fetch_one(session_query)
            if session_result:
                self.current_session_id = session_result['id']
                logging.info(f"Started session {session_name} with ID {self.current_session_id}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error starting session: {e}")
            return False
    
    def end_session(self) -> bool:
        """End the current detection session"""
        if not self.current_session_id or not self.current_db:
            return False
        
        try:
            query = '''UPDATE detection_sessions 
                      SET end_time = CURRENT_TIMESTAMP 
                      WHERE id = ?'''
            
            self.current_db.execute_query(query, (self.current_session_id,))
            self.current_session_id = None
            logging.info("Session ended successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error ending session: {e}")
            return False
    
    def save_detection(self, vehicle_type: str, direction: str, 
                      confidence: float, bbox: List[int], 
                      track_id: int, line_crossed: str,
                      speed_estimate: float = None) -> bool:
        """Save a single vehicle detection"""
        if not self.current_session_id or not self.current_db:
            return False
        
        try:
            query = '''INSERT INTO vehicle_detections 
                      (session_id, vehicle_type, direction, confidence,
                       bbox_x1, bbox_y1, bbox_x2, bbox_y2, track_id,
                       line_crossed, speed_estimate)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
            
            self.current_db.execute_query(
                query,
                (self.current_session_id, vehicle_type, direction, confidence,
                 bbox[0], bbox[1], bbox[2], bbox[3], track_id,
                 line_crossed, speed_estimate)
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Error saving detection: {e}")
            return False
    
    def save_statistics(self, statistics: Dict[str, Dict[str, int]]) -> bool:
        """Save traffic statistics"""
        if not self.current_session_id or not self.current_db:
            return False
        
        try:
            # Clear existing statistics for current session
            delete_query = "DELETE FROM traffic_statistics WHERE session_id = ?"
            self.current_db.execute_query(delete_query, (self.current_session_id,))
            
            # Insert new statistics
            insert_query = '''INSERT INTO traffic_statistics 
                             (session_id, vehicle_type, direction, count, time_period)
                             VALUES (?, ?, ?, ?, ?)'''
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for direction, vehicles in statistics.items():
                for vehicle_type, count in vehicles.items():
                    self.current_db.execute_query(
                        insert_query,
                        (self.current_session_id, vehicle_type, direction, count, current_time)
                    )
            
            return True
            
        except Exception as e:
            logging.error(f"Error saving statistics: {e}")
            return False
    
    def get_session_data(self, session_id: int = None) -> Optional[Dict]:
        """Get data for a specific session"""
        if not self.current_db:
            return None
        
        target_session = session_id or self.current_session_id
        if not target_session:
            return None
        
        try:
            # Get session info
            session_query = "SELECT * FROM detection_sessions WHERE id = ?"
            session_data = self.current_db.fetch_one(session_query, (target_session,))
            
            if not session_data:
                return None
            
            # Get detections
            detections_query = "SELECT * FROM vehicle_detections WHERE session_id = ? ORDER BY timestamp"
            detections = self.current_db.fetch_all(detections_query, (target_session,))
            
            # Get statistics
            stats_query = "SELECT * FROM traffic_statistics WHERE session_id = ?"
            statistics = self.current_db.fetch_all(stats_query, (target_session,))
            
            return {
                'session': session_data,
                'detections': detections,
                'statistics': statistics
            }
            
        except Exception as e:
            logging.error(f"Error getting session data: {e}")
            return None
    
    def export_data(self, format_type: str, output_path: str, 
                   session_id: int = None, date_range: Tuple[str, str] = None) -> bool:
        """Export data in various formats"""
        if not self.current_db:
            return False
        
        try:
            # Build query based on filters
            base_query = '''
                SELECT ds.session_name, ds.start_time, ds.end_time,
                       vd.timestamp, vd.vehicle_type, vd.direction,
                       vd.confidence, vd.track_id, vd.line_crossed
                FROM detection_sessions ds
                LEFT JOIN vehicle_detections vd ON ds.id = vd.session_id
                WHERE 1=1
            '''
            
            params = []
            if session_id:
                base_query += " AND ds.id = ?"
                params.append(session_id)
            
            if date_range:
                base_query += " AND ds.start_time BETWEEN ? AND ?"
                params.extend(date_range)
            
            base_query += " ORDER BY ds.start_time, vd.timestamp"
            
            data = self.current_db.fetch_all(base_query, tuple(params) if params else None)
            
            if not data:
                return False
            
            # Export based on format
            if format_type.lower() == 'csv':
                self._export_csv(data, output_path)
            elif format_type.lower() == 'excel':
                self._export_excel(data, output_path)
            elif format_type.lower() == 'json':
                self._export_json(data, output_path)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error exporting data: {e}")
            return False
    
    def _export_csv(self, data: List[Dict], output_path: str):
        """Export data to CSV format"""
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            if data:
                writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
    
    def _export_excel(self, data: List[Dict], output_path: str):
        """Export data to Excel format"""
        df = pd.DataFrame(data)
        df.to_excel(output_path, index=False, engine='openpyxl')
    
    def _export_json(self, data: List[Dict], output_path: str):
        """Export data to JSON format"""
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, default=str)
    
    def get_available_databases(self) -> Dict[str, bool]:
        """Get list of available database types"""
        return {
            'sqlite': True,
            'mysql': MYSQL_AVAILABLE,
            'postgresql': POSTGRESQL_AVAILABLE
        }
    
    def backup_database(self, backup_path: str) -> bool:
        """Create database backup"""
        if not self.current_db or not isinstance(self.current_db, SQLiteDatabase):
            logging.warning("Backup only supported for SQLite currently")
            return False
        
        try:
            import shutil
            shutil.copy2(self.current_db.db_path, backup_path)
            logging.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logging.error(f"Backup failed: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup"""
        if not isinstance(self.current_db, SQLiteDatabase):
            logging.warning("Restore only supported for SQLite currently")
            return False
        
        try:
            import shutil
            self.current_db.disconnect()
            shutil.copy2(backup_path, self.current_db.db_path)
            self.current_db.connect()
            logging.info(f"Database restored from {backup_path}")
            return True
        except Exception as e:
            logging.error(f"Restore failed: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get database performance statistics"""
        if not self.current_db:
            return {}
        
        try:
            stats = {}
            
            # Get total records
            tables = ['detection_sessions', 'vehicle_detections', 'traffic_statistics']
            for table in tables:
                count_query = f"SELECT COUNT(*) as count FROM {table}"
                result = self.current_db.fetch_one(count_query)
                stats[f'{table}_count'] = result['count'] if result else 0
            
            # Get recent activity
            recent_query = '''
                SELECT COUNT(*) as recent_detections 
                FROM vehicle_detections 
                WHERE timestamp > datetime('now', '-1 hour')
            '''
            if isinstance(self.current_db, MySQLDatabase):
                recent_query = '''
                    SELECT COUNT(*) as recent_detections 
                    FROM vehicle_detections 
                    WHERE timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                '''
            elif isinstance(self.current_db, PostgreSQLDatabase):
                recent_query = '''
                    SELECT COUNT(*) as recent_detections 
                    FROM vehicle_detections 
                    WHERE timestamp > NOW() - INTERVAL '1 hour'
                '''
            
            result = self.current_db.fetch_one(recent_query)
            stats['recent_detections'] = result['recent_detections'] if result else 0
            
            return stats
            
        except Exception as e:
            logging.error(f"Error getting performance stats: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Clean up old data beyond specified days"""
        if not self.current_db:
            return False
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Delete old detections first (foreign key constraint)
            delete_detections = '''
                DELETE FROM vehicle_detections 
                WHERE session_id IN (
                    SELECT id FROM detection_sessions 
                    WHERE start_time < ?
                )
            '''
            
            # Delete old statistics
            delete_stats = '''
                DELETE FROM traffic_statistics 
                WHERE session_id IN (
                    SELECT id FROM detection_sessions 
                    WHERE start_time < ?
                )
            '''
            
            # Delete old sessions
            delete_sessions = "DELETE FROM detection_sessions WHERE start_time < ?"
            
            self.current_db.execute_query(delete_detections, (cutoff_date,))
            self.current_db.execute_query(delete_stats, (cutoff_date,))
            self.current_db.execute_query(delete_sessions, (cutoff_date,))
            
            logging.info(f"Cleaned up data older than {days_to_keep} days")
            return True
            
        except Exception as e:
            logging.error(f"Error cleaning up data: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from current database"""
        if self.current_db:
            self.current_db.disconnect()
            self.connection_status = False
            logging.info("Database disconnected")

# Create global database manager instance
db_manager = EnhancedDatabaseManager()