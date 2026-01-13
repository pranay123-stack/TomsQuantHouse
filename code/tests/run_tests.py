#!/usr/bin/env python3
"""
Test runner script for the API integration testing suite.
Provides convenient commands for running different test categories.
"""
import sys
import argparse
import subprocess
from pathlib import Path

def run_command(cmd: list, description: str):
    """Run a command and handle output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ {description} FAILED")
        return False
    else:
        print(f"\n✅ {description} PASSED")
        return True

def main():
    parser = argparse.ArgumentParser(description="API Integration Test Runner")
    
    parser.add_argument(
        "category",
        nargs="?",
        choices=["all", "integration", "performance", "e2e", "unit", "health", "errors", "memory"],
        default="all",
        help="Test category to run"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true", 
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--slow",
        action="store_true",
        help="Include slow tests"
    )
    
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run tests against live services (not mocks)"
    )
    
    parser.add_argument(
        "--report-dir",
        default="reports",
        help="Directory for test reports"
    )
    
    args = parser.parse_args()
    
    # Create reports directory
    Path(args.report_dir).mkdir(exist_ok=True)
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add common options
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend([
            "--cov=src",
            f"--cov-report=html:{args.report_dir}/coverage",
            f"--cov-report=xml:{args.report_dir}/coverage.xml",
            f"--cov-report=term-missing"
        ])
    
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    # Add report options
    cmd.extend([
        f"--junitxml={args.report_dir}/junit.xml",
        "--html", f"{args.report_dir}/report.html",
        "--self-contained-html"
    ])
    
    # Test markers
    if not args.slow:
        cmd.append("-m")
        cmd.append("not slow")
    
    if not args.live:
        cmd.append("-m")
        if "not slow" in cmd:
            cmd[-1] += " and not live"
        else:
            cmd.append("not live")
    
    # Add test paths
    test_paths = ["tests/"]
    
    # Category-specific configuration
    success = True
    
    if args.category == "all":
        print("🚀 Running ALL tests...")
        success = run_command(cmd + test_paths, "All Tests")
        
    elif args.category == "integration":
        print("🔗 Running INTEGRATION tests...")
        integration_cmd = cmd + ["-m", "integration"] + test_paths
        success = run_command(integration_cmd, "Integration Tests")
        
    elif args.category == "performance":
        print("⚡ Running PERFORMANCE tests...")
        perf_cmd = cmd + ["-m", "performance", "-v"] + test_paths
        success = run_command(perf_cmd, "Performance Tests")
        
    elif args.category == "e2e":
        print("🔄 Running END-TO-END tests...")
        e2e_cmd = cmd + ["-m", "e2e", "-v"] + test_paths
        success = run_command(e2e_cmd, "End-to-End Tests")
        
    elif args.category == "unit":
        print("🧪 Running UNIT tests...")
        unit_cmd = cmd + ["-m", "unit"] + test_paths
        success = run_command(unit_cmd, "Unit Tests")
        
    elif args.category == "health":
        print("❤️  Running HEALTH CHECK tests...")
        health_cmd = cmd + ["tests/integration/test_health_checks.py", "-v"] + test_paths
        success = run_command(health_cmd, "Health Check Tests")
        
    elif args.category == "errors":
        print("🚨 Running ERROR HANDLING tests...")
        error_cmd = cmd + ["tests/integration/test_error_handling.py", "-v"] + test_paths
        success = run_command(error_cmd, "Error Handling Tests")
        
    elif args.category == "memory":
        print("🧠 Running LETTA MEMORY tests...")
        memory_cmd = cmd + ["tests/integration/test_letta_memory.py", "-v"] + test_paths
        success = run_command(memory_cmd, "Letta Memory Tests")
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 ALL TESTS PASSED!")
        print(f"📊 Reports generated in: {args.report_dir}/")
        print(f"   - HTML Report: {args.report_dir}/report.html")
        if args.coverage:
            print(f"   - Coverage: {args.report_dir}/coverage/index.html")
        print(f"   - JUnit: {args.report_dir}/junit.xml")
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"📊 Check reports in: {args.report_dir}/")
        sys.exit(1)

if __name__ == "__main__":
    main()