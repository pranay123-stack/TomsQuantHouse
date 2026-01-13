#!/usr/bin/env python3
"""
Letta Server Test Script
Tests Letta server functionality, agent creation, and memory persistence
"""

import os
import sys
import time
import json
import requests
import subprocess
from typing import Dict, List, Any
from datetime import datetime

class LettaServerTester:
    def __init__(self, base_url: str = "http://localhost:8283", api_key: str = "your-secret-api-key-here"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if success else "FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        print(f"[{status}] {test_name}")
        if message:
            print(f"    {message}")
    
    def test_server_health(self) -> bool:
        """Test if Letta server is running and responsive"""
        try:
            response = requests.get(f"{self.base_url}/health", headers=self.headers, timeout=10)
            if response.status_code == 200:
                self.log_test("Server Health Check", True, f"Server is running on {self.base_url}")
                return True
            else:
                self.log_test("Server Health Check", False, f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_test("Server Health Check", False, str(e))
            return False
    
    def test_database_connection(self) -> bool:
        """Test PostgreSQL database connection"""
        try:
            # Try to get agents to test database connectivity
            response = requests.get(f"{self.base_url}/api/agents", headers=self.headers, timeout=10)
            if response.status_code == 200:
                agents = response.json()
                self.log_test("Database Connection", True, f"Connected to database, found {len(agents)} agents")
                return True
            else:
                self.log_test("Database Connection", False, f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_test("Database Connection", False, str(e))
            return False
    
    def test_create_simple_agent(self) -> str:
        """Test creating a simple test agent"""
        agent_config = {
            "name": f"test_agent_{int(time.time())}",
            "description": "Test agent for functionality verification",
            "system_prompt": "You are a test agent created to verify Letta server functionality.",
            "model": "gpt-3.5-turbo",
            "metadata": {
                "test_agent": True,
                "created_for": "functionality_test"
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/agents",
                headers=self.headers,
                json=agent_config,
                timeout=30
            )
            
            if response.status_code == 200:
                agent = response.json()
                agent_id = agent.get("id", "")
                self.log_test("Create Simple Agent", True, f"Created agent: {agent_id}")
                return agent_id
            else:
                self.log_test("Create Simple Agent", False, f"HTTP {response.status_code}: {response.text}")
                return ""
        except requests.exceptions.RequestException as e:
            self.log_test("Create Simple Agent", False, str(e))
            return ""
    
    def test_memory_operations(self, agent_id: str) -> bool:
        """Test memory block creation, retrieval, and updates"""
        if not agent_id:
            self.log_test("Memory Operations", False, "No agent ID provided")
            return False
        
        try:
            # Test 1: Create memory block
            memory_config = {
                "block_type": "test_context",
                "title": "Test Memory Block",
                "content": f"This is a test memory block created at {datetime.now()}",
                "value_type": "string",
                "metadata": {
                    "test": True,
                    "created_by": "functionality_test"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/agents/{agent_id}/memory",
                headers=self.headers,
                json=memory_config,
                timeout=10
            )
            
            if response.status_code != 200:
                self.log_test("Memory Operations", False, f"Failed to create memory block: {response.status_code}")
                return False
            
            memory_block = response.json()
            block_id = memory_block.get("id", "")
            
            # Test 2: Retrieve memory blocks
            response = requests.get(
                f"{self.base_url}/api/agents/{agent_id}/memory",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                self.log_test("Memory Operations", False, f"Failed to retrieve memory: {response.status_code}")
                return False
            
            memory_data = response.json()
            blocks = memory_data.get("blocks", [])
            
            # Verify our test block exists
            test_block_found = any(block.get("title") == "Test Memory Block" for block in blocks)
            
            if not test_block_found:
                self.log_test("Memory Operations", False, "Test memory block not found in retrieval")
                return False
            
            # Test 3: Update memory block
            if block_id:
                update_data = {
                    "content": f"Updated test memory block at {datetime.now()}",
                    "metadata": {"updated": True}
                }
                
                response = requests.put(
                    f"{self.base_url}/api/agents/{agent_id}/memory/{block_id}",
                    headers=self.headers,
                    json=update_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    self.log_test("Memory Operations", True, "Successfully created, retrieved, and updated memory block")
                    return True
                else:
                    self.log_test("Memory Operations", False, f"Failed to update memory block: {response.status_code}")
                    return False
            else:
                self.log_test("Memory Operations", False, "No block ID returned from creation")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Memory Operations", False, str(e))
            return False
    
    def test_agent_communication(self, agent_id: str) -> bool:
        """Test sending messages to agent and getting responses"""
        if not agent_id:
            self.log_test("Agent Communication", False, "No agent ID provided")
            return False
        
        try:
            message_data = {
                "agent_id": agent_id,
                "message": "Hello, can you introduce yourself and tell me about your capabilities?",
                "role": "user",
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/agents/message",
                headers=self.headers,
                json=message_data,
                timeout=60  # Longer timeout for AI response
            )
            
            if response.status_code == 200:
                result = response.json()
                messages = result.get("messages", [])
                if messages and len(messages) > 0:
                    last_message = messages[-1]
                    if last_message.get("role") == "assistant":
                        self.log_test("Agent Communication", True, "Successfully communicated with agent")
                        return True
                    else:
                        self.log_test("Agent Communication", False, "No assistant response received")
                        return False
                else:
                    self.log_test("Agent Communication", False, "No messages in response")
                    return False
            else:
                self.log_test("Agent Communication", False, f"HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Agent Communication", False, str(e))
            return False
    
    def test_persistence_after_restart(self) -> bool:
        """Test that agent data persists after a server restart"""
        try:
            # Get current agent count
            response = requests.get(f"{self.base_url}/api/agents", headers=self.headers, timeout=10)
            if response.status_code != 200:
                self.log_test("Persistence Test", False, "Cannot get agent count")
                return False
            
            agents_before = len(response.json())
            
            # Simulate restart by waiting a moment and checking if server persists
            print("    Waiting 10 seconds to simulate restart...")
            time.sleep(10)
            
            # Check if agents still exist
            response = requests.get(f"{self.base_url}/api/agents", headers=self.headers, timeout=10)
            if response.status_code != 200:
                self.log_test("Persistence Test", False, "Server not responding after restart")
                return False
            
            agents_after = len(response.json())
            
            if agents_after == agents_before:
                self.log_test("Persistence Test", True, f"Agent count maintained: {agents_after}")
                return True
            else:
                self.log_test("Persistence Test", False, f"Agent count changed: {agents_before} -> {agents_after}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Persistence Test", False, str(e))
            return False
    
    def test_trading_agents_functionality(self) -> bool:
        """Test functionality of pre-created trading agents"""
        try:
            # Get all agents
            response = requests.get(f"{self.base_url}/api/agents", headers=self.headers, timeout=10)
            if response.status_code != 200:
                self.log_test("Trading Agents Test", False, "Cannot retrieve agents")
                return False
            
            agents = response.json()
            
            # Look for trading agents
            trading_agents = [
                agent for agent in agents
                if any(keyword in agent.get("name", "").lower() 
                      for keyword in ["trading", "strategist", "analyst", "risk"])
            ]
            
            if not trading_agents:
                self.log_test("Trading Agents Test", False, "No trading agents found")
                return False
            
            # Test communication with at least one trading agent
            test_agent = trading_agents[0]
            agent_id = test_agent.get("id", "")
            
            message_data = {
                "agent_id": agent_id,
                "message": "What trading strategies do you have stored in your memory?",
                "role": "user",
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/agents/message",
                headers=self.headers,
                json=message_data,
                timeout=60
            )
            
            if response.status_code == 200:
                self.log_test("Trading Agents Test", True, f"Successfully queried {len(trading_agents)} trading agents")
                return True
            else:
                self.log_test("Trading Agents Test", False, f"Failed to query trading agent: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.log_test("Trading Agents Test", False, str(e))
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results"""
        print("Starting Letta Server Functionality Tests")
        print("=" * 50)
        
        # Test 1: Server health
        if not self.test_server_health():
            print("\nServer is not running. Please start the Letta server first.")
            return self.test_results
        
        # Test 2: Database connection
        self.test_database_connection()
        
        # Test 3: Create simple agent
        test_agent_id = self.test_create_simple_agent()
        
        # Test 4: Memory operations
        if test_agent_id:
            self.test_memory_operations(test_agent_id)
            
            # Test 5: Agent communication
            self.test_agent_communication(test_agent_id)
        
        # Test 6: Persistence
        self.test_persistence_after_restart()
        
        # Test 7: Trading agents
        self.test_trading_agents_functionality()
        
        return self.test_results
    
    def generate_report(self) -> str:
        """Generate test report"""
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        total = len(self.test_results)
        
        report = f"""
Letta Server Test Report
Generated: {datetime.now().isoformat()}
{'=' * 50}

Test Summary:
- Total Tests: {total}
- Passed: {passed}
- Failed: {total - passed}
- Success Rate: {(passed/total*100):.1f}%

Detailed Results:
"""
        
        for result in self.test_results:
            status_emoji = "✅" if result["status"] == "PASS" else "❌"
            report += f"{status_emoji} {result['test']}: {result['status']}\n"
            if result['message']:
                report += f"    {result['message']}\n"
            report += f"    Time: {result['timestamp']}\n\n"
        
        return report

def main():
    """Main test execution"""
    tester = LettaServerTester()
    
    # Check if Letta server is running
    try:
        response = requests.get("http://localhost:8283/health", timeout=5)
        print("Letta server is running. Starting tests...")
    except requests.exceptions.RequestException:
        print("ERROR: Letta server is not running!")
        print("Please start the Letta server first:")
        print("  cd /workspace/code/letta && docker-compose up -d")
        print("  OR")
        print("  python create_agents.py")
        sys.exit(1)
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Generate and save report
    report = tester.generate_report()
    
    # Print report
    print("\n" + report)
    
    # Save report to file
    with open("/workspace/code/letta/test_report.txt", "w") as f:
        f.write(report)
    
    print(f"Test report saved to: /workspace/code/letta/test_report.txt")
    
    # Save results as JSON
    with open("/workspace/code/letta/test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Test results saved to: /workspace/code/letta/test_results.json")
    
    # Return exit code based on results
    failed_tests = [r for r in results if r["status"] == "FAIL"]
    if failed_tests:
        print(f"\n❌ {len(failed_tests)} test(s) failed!")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(results)} tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()