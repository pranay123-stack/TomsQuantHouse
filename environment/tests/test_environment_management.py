#!/usr/bin/env python3
"""
Test Suite for Environment Management System

This test suite validates all components of the environment and secrets management system.
"""

import unittest
import os
import sys
import tempfile
import shutil
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from secrets.secrets_manager import SecretsManager, SecretEntry
from config_manager import ConfigManager, EnvironmentConfig, EnvironmentType, ValidationRule
from tools.backup_migration import BackupManager, BackupType, MigrationManager
from tools.testing_validation import EnvironmentValidator, EnvironmentTester, TestResult
from tools.deployment_automation import DeploymentManager, DeploymentStatus
from environment_manager import EnvironmentManagementSystem

class TestSecretsManager(unittest.TestCase):
    """Test secrets management functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.secrets_manager = SecretsManager()
        
        # Create test data
        self.test_secret_name = "test_secret"
        self.test_secret_value = "test_password_123"
        self.test_environment = "test"
    
    def tearDown(self):
        # Cleanup
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_store_and_retrieve_secret(self):
        """Test storing and retrieving a secret"""
        # Store secret
        success = self.secrets_manager.store_secret(
            self.test_secret_name, 
            self.test_secret_value, 
            self.test_environment
        )
        self.assertTrue(success)
        
        # Retrieve secret
        retrieved_value = self.secrets_manager.get_secret(self.test_secret_name)
        self.assertEqual(retrieved_value, self.test_secret_value)
    
    def test_secret_rotation(self):
        """Test secret rotation"""
        # Store initial secret
        self.secrets_manager.store_secret(
            self.test_secret_name, 
            self.test_secret_value, 
            self.test_environment
        )
        
        # Rotate secret
        new_value = "new_password_456"
        success = self.secrets_manager.rotate_secret(self.test_secret_name, new_value)
        self.assertTrue(success)
        
        # Verify new value
        retrieved_value = self.secrets_manager.get_secret(self.test_secret_name)
        self.assertEqual(retrieved_value, new_value)
    
    def test_generate_secret(self):
        """Test secret generation"""
        generated = self.secrets_manager.generate_secret("test_generation", 32)
        self.assertIsInstance(generated, str)
        self.assertGreater(len(generated), 20)
    
    def test_list_secrets(self):
        """Test listing secrets"""
        # Store multiple secrets
        self.secrets_manager.store_secret("secret1", "value1", "dev")
        self.secrets_manager.store_secret("secret2", "value2", "staging")
        self.secrets_manager.store_secret("secret3", "value3", "prod")
        
        # List all secrets
        all_secrets = self.secrets_manager.db.list_secrets()
        self.assertEqual(len(all_secrets), 3)
        
        # List by environment
        dev_secrets = self.secrets_manager.db.list_secrets("dev")
        self.assertEqual(len(dev_secrets), 1)
        self.assertEqual(dev_secrets[0].name, "secret1")

class TestConfigManager(unittest.TestCase):
    """Test configuration management functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)
        
        # Create test configuration
        self.test_config_data = {
            "environment": {
                "name": "test",
                "type": "development"
            },
            "app": {
                "host": "localhost",
                "port": 3000,
                "database": {
                    "host": "localhost",
                    "port": 5432
                }
            },
            "security": {
                "jwt": {
                    "secret": "test_secret_key_123456789",
                    "expiration": "24h"
                }
            }
        }
        
        # Write test configuration file
        with open(os.path.join(self.temp_dir, "test.yaml"), "w") as f:
            yaml.dump(self.test_config_data, f)
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_load_config(self):
        """Test configuration loading"""
        config = self.config_manager.load_config("test")
        self.assertIsNotNone(config)
        self.assertEqual(config.name, "test")
        self.assertEqual(config.type, EnvironmentType.DEVELOPMENT)
        self.assertEqual(config.get("app.port"), 3000)
    
    def test_update_config(self):
        """Test configuration updates"""
        config = self.config_manager.load_config("test")
        original_port = config.get("app.port")
        
        # Update configuration
        success = self.config_manager.update_config(
            "test", "app.port", 8080, "test_user", "Port change"
        )
        self.assertTrue(success)
        
        # Verify update
        new_port = self.config_manager.get_config("test", "app.port")
        self.assertEqual(new_port, 8080)
        self.assertNotEqual(new_port, original_port)
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Add validation rule
        rule = ValidationRule(
            path="app.custom_field",
            required=True,
            type="str",
            min_length=5
        )
        self.config_manager.validator.add_rule(rule)
        
        config = self.config_manager.load_config("test")
        errors = self.config_manager.validator.validate(config)
        
        # Should have validation error for missing custom_field
        self.assertTrue(any("custom_field" in error for error in errors))

class TestBackupManager(unittest.TestCase):
    """Test backup and migration functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.backup_manager = BackupManager(self.temp_dir)
        
        # Create test configuration directory
        self.config_dir = os.path.join(self.temp_dir, "configs")
        os.makedirs(self.config_dir)
        
        test_config = {
            "environment": {"name": "test", "type": "development"},
            "app": {"host": "localhost", "port": 3000}
        }
        
        with open(os.path.join(self.config_dir, "test.yaml"), "w") as f:
            yaml.dump(test_config, f)
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_backup(self):
        """Test backup creation"""
        backup_id = self.backup_manager.create_backup(
            "test", BackupType.FULL, "Test backup"
        )
        self.assertIsNotNone(backup_id)
        self.assertTrue(backup_id.startswith("backup_"))
    
    def test_verify_backup(self):
        """Test backup verification"""
        # Create backup
        backup_id = self.backup_manager.create_backup(
            "test", BackupType.FULL, "Test backup"
        )
        
        # Verify backup
        is_valid = self.backup_manager.verify_backup(backup_id)
        self.assertTrue(is_valid)
    
    def test_list_backups(self):
        """Test backup listing"""
        # Create multiple backups
        backup1 = self.backup_manager.create_backup("test1", BackupType.FULL, "Backup 1")
        backup2 = self.backup_manager.create_backup("test2", BackupType.FULL, "Backup 2")
        
        # List backups
        backups = self.backup_manager.list_backups(limit=10)
        self.assertGreaterEqual(len(backups), 2)
        
        # Verify backup IDs are in the list
        backup_ids = [b.backup_id for b in backups]
        self.assertIn(backup1, backup_ids)
        self.assertIn(backup2, backup_ids)

class TestEnvironmentTester(unittest.TestCase):
    """Test environment testing and validation"""
    
    def setUp(self):
        self.tester = EnvironmentTester()
        self.test_config_data = {
            "environment": {
                "name": "test",
                "type": "development"
            },
            "app": {
                "host": "localhost",
                "port": 3000,
                "database": {
                    "host": "localhost",
                    "port": 5432
                },
                "redis": {
                    "host": "localhost",
                    "port": 6379
                },
                "base_url": "http://localhost:3000"
            },
            "security": {
                "jwt": {
                    "secret": "test_secret_key_123456789012345",
                    "expiration": "24h"
                },
                "cors": {
                    "enabled": True,
                    "origins": ["http://localhost:3000"]
                }
            },
            "monitoring": {
                "health_checks": {
                    "endpoint": "/health"
                }
            }
        }
    
    def test_run_validation(self):
        """Test environment validation"""
        results = self.tester.run_full_validation("test", self.test_config_data)
        
        self.assertIn("summary", results)
        self.assertIn("results", results)
        self.assertIn("timestamp", results)
        
        summary = results["summary"]
        self.assertIn("total_tests", summary)
        self.assertIn("passed", summary)
        self.assertIn("success_rate", summary)
        
        # Should have run multiple checks
        self.assertGreater(summary["total_tests"], 0)

class TestDeploymentManager(unittest.TestCase):
    """Test deployment automation functionality"""
    
    def setUp(self):
        self.deployment_manager = DeploymentManager()
    
    def test_create_deployment(self):
        """Test deployment creation"""
        deployment_id = self.deployment_manager.create_deployment(
            "development", "v1.0.0", "standard"
        )
        
        self.assertIsNotNone(deployment_id)
        self.assertTrue(deployment_id.startswith("deploy_"))
        
        # Check deployment status
        status = self.deployment_manager.get_deployment_status(deployment_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["environment"], "development")
        self.assertEqual(status["version"], "v1.0.0")
        self.assertEqual(status["status"], "pending")
    
    def test_canary_deployment(self):
        """Test canary deployment"""
        deployment_id = self.deployment_manager.canary_deployment(
            "staging", "v1.0.0", canary_percentage=10
        )
        
        status = self.deployment_manager.get_deployment_status(deployment_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["canary_percentage"], 10)

class TestEnvironmentManagementSystem(unittest.TestCase):
    """Test the main environment management system"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "templates")
        os.makedirs(self.config_dir)
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        
        # Create test configuration files
        test_configs = {
            "development.yaml": {
                "environment": {"name": "development", "type": "development"},
                "app": {"host": "localhost", "port": 3000}
            },
            "staging.yaml": {
                "environment": {"name": "staging", "type": "staging"},
                "app": {"host": "staging.example.com", "port": 8080}
            },
            "production.yaml": {
                "environment": {"name": "production", "type": "production"},
                "app": {"host": "prod.example.com", "port": 8080}
            }
        }
        
        for filename, config in test_configs.items():
            with open(os.path.join(self.config_dir, filename), "w") as f:
                yaml.dump(config, f)
        
        # Initialize system
        self.env_mgmt = EnvironmentManagementSystem(self.config_dir, self.backup_dir)
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialize_system(self):
        """Test system initialization"""
        success = self.env_mgmt.initialize_system(["development", "staging", "production"])
        self.assertTrue(success)
        
        # Check that configurations were loaded
        configs = self.env_mgmt.config_manager.list_configs()
        self.assertGreaterEqual(len(configs), 0)
    
    def test_show_status(self):
        """Test system status display"""
        status = self.env_mgmt.show_status()
        
        self.assertIn("timestamp", status)
        self.assertIn("system", status)
        self.assertIn("environments", status)
        
        system_status = status["system"]
        self.assertIn("status", system_status)
        self.assertIn("secrets_count", system_status)
        self.assertIn("configs_count", system_status)
    
    def test_validate_environment(self):
        """Test environment validation"""
        result = self.env_mgmt.validate_environment("development")
        
        self.assertIn("environment", result)
        self.assertIn("valid", result)
        self.assertEqual(result["environment"], "development")
    
    def test_health_check(self):
        """Test comprehensive health check"""
        health = self.env_mgmt.run_health_check()
        
        self.assertIn("timestamp", health)
        self.assertIn("overall_status", health)
        self.assertIn("components", health)
        
        components = health["components"]
        self.assertIn("secrets_management", components)
        self.assertIn("config_management", components)
        self.assertIn("backup_system", components)
        self.assertIn("testing_system", components)
        self.assertIn("deployment_system", components)

class IntegrationTest(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "templates")
        os.makedirs(self.config_dir)
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        
        # Create comprehensive test configuration
        test_config = {
            "environment": {
                "name": "test",
                "type": "development",
                "debug": True
            },
            "app": {
                "host": "localhost",
                "port": 3000,
                "base_url": "http://localhost:3000",
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "test_db"
                },
                "redis": {
                    "host": "localhost",
                    "port": 6379
                }
            },
            "security": {
                "jwt": {
                    "secret": "test_secret_key_123456789012345",
                    "expiration": "24h"
                },
                "cors": {
                    "enabled": True,
                    "origins": ["http://localhost:3000"]
                }
            },
            "monitoring": {
                "health_checks": {
                    "endpoint": "/health"
                }
            }
        }
        
        with open(os.path.join(self.config_dir, "test.yaml"), "w") as f:
            yaml.dump(test_config, f)
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_full_workflow(self):
        """Test complete workflow from initialization to deployment"""
        # Initialize system
        env_mgmt = EnvironmentManagementSystem(self.config_dir, self.backup_dir)
        init_success = env_mgmt.initialize_system(["test"])
        self.assertTrue(init_success)
        
        # Store a secret
        secret_stored = env_mgmt.secrets_manager.store_secret(
            "test_secret", "test_value", "test"
        )
        self.assertTrue(secret_stored)
        
        # Retrieve the secret
        secret_retrieved = env_mgmt.secrets_manager.get_secret("test_secret")
        self.assertEqual(secret_retrieved, "test_value")
        
        # Validate environment
        validation_result = env_mgmt.validate_environment("test")
        self.assertIn("valid", validation_result)
        
        # Create backup
        backup_id = env_mgmt.create_backup("test", "full", "Integration test backup")
        self.assertIsNotNone(backup_id)
        
        # Run health check
        health = env_mgmt.run_health_check()
        self.assertIn("overall_status", health)
        
        # Check system status
        status = env_mgmt.show_status()
        self.assertIn("system", status)
        
        print("✓ Integration test completed successfully")

def run_performance_test():
    """Performance test for the system"""
    import time
    
    print("Running performance tests...")
    
    # Test secrets operations
    start_time = time.time()
    secrets_manager = SecretsManager()
    
    for i in range(100):
        secrets_manager.store_secret(f"perf_test_{i}", f"value_{i}", "perf")
        secrets_manager.get_secret(f"perf_test_{i}")
    
    secrets_time = time.time() - start_time
    print(f"✓ 100 secret operations completed in {secrets_time:.2f} seconds")
    
    # Test configuration operations
    start_time = time.time()
    config_manager = ConfigManager()
    
    for i in range(50):
        config_manager.update_config("development", f"test.field{i}", f"value{i}")
    
    config_time = time.time() - start_time
    print(f"✓ 50 configuration updates completed in {config_time:.2f} seconds")
    
    # Test validation
    start_time = time.time()
    tester = EnvironmentTester()
    
    test_config = {
        "environment": {"name": "perf", "type": "development"},
        "app": {"host": "localhost", "port": 3000}
    }
    
    results = tester.run_full_validation("perf", test_config)
    
    validation_time = time.time() - start_time
    print(f"✓ Environment validation completed in {validation_time:.2f} seconds")
    print(f"  Tests run: {results['summary']['total_tests']}")
    print(f"  Success rate: {results['summary']['success_rate']:.1f}%")

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Management System Tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not any([args.unit, args.integration, args.performance]):
        # Run all tests by default
        args.unit = True
        args.integration = True
        args.performance = True
    
    # Set up test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    if args.unit:
        # Add unit test classes
        unit_test_classes = [
            TestSecretsManager,
            TestConfigManager,
            TestBackupManager,
            TestEnvironmentTester,
            TestDeploymentManager,
            TestEnvironmentManagementSystem
        ]
        
        for test_class in unit_test_classes:
            tests = loader.loadTestsFromTestCase(test_class)
            suite.addTests(tests)
        
        print("Running unit tests...")
    
    if args.integration:
        # Add integration test
        tests = loader.loadTestsFromTestCase(IntegrationTest)
        suite.addTests(tests)
        print("Running integration tests...")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    
    # Run performance tests
    if args.performance:
        print("\n" + "="*50)
        print("Performance Tests")
        print("="*50)
        run_performance_test()
    
    # Summary
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # Exit with appropriate code
    if result.failures or result.errors:
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()