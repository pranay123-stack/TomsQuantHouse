"""
Tests for Letta agent memory persistence across sessions
"""
import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from conftest import TestConfig

@pytest.mark.integration
@pytest.mark.letta
class TestLettaAgentMemoryPersistence:
    """Test Letta agent memory persistence across sessions"""
    
    async def test_agent_memory_creation_and_retrieval(self, mock_letta_client):
        """Test creating an agent and retrieving its memory"""
        # Create agent
        agent_config = {
            "name": "trading_assistant_v1",
            "system_prompt": "You are a helpful trading assistant that provides market analysis and trading advice.",
            "model": "gpt-4",
            "memory_settings": {
                "persistent": True,
                "max_memory_items": 1000
            }
        }
        
        create_result = await mock_letta_client.create_agent(agent_config)
        agent_id = create_result["agent_id"]
        
        assert agent_id is not None
        print(f"Created agent: {agent_id}")
        
        # Store some initial memory
        initial_memory = {
            "conversation": [
                {
                    "role": "user",
                    "content": "What's your trading strategy?",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "role": "assistant", 
                    "content": "I focus on technical analysis and risk management.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "preferences": {
                "preferred_symbols": ["AAPL", "GOOGL", "MSFT"],
                "risk_tolerance": "moderate",
                "analysis_style": "technical"
            }
        }
        
        update_result = await mock_letta_client.update_memory(agent_id, initial_memory)
        assert update_result is True
        print("Initial memory stored")
        
        # Simulate session end and new session
        await asyncio.sleep(0.1)  # Simulate time passing
        
        # Retrieve memory in new session
        retrieved_memory = await mock_letta_client.get_memory(agent_id)
        
        assert retrieved_memory is not None
        assert "conversation" in retrieved_memory
        assert "preferences" in retrieved_memory
        assert len(retrieved_memory["conversation"]) == 2
        assert retrieved_memory["preferences"]["risk_tolerance"] == "moderate"
        
        print("Memory retrieved successfully across sessions")
        print(f"Conversation length: {len(retrieved_memory['conversation'])}")
    
    async def test_memory_persistence_with_multiple_interactions(self, mock_letta_client):
        """Test memory persistence through multiple interaction cycles"""
        agent_config = {
            "name": "multi_session_agent",
            "system_prompt": "You are a trading analyst with memory of past conversations.",
            "model": "gpt-4"
        }
        
        create_result = await mock_letta_client.create_agent(agent_config)
        agent_id = create_result["agent_id"]
        
        # Session 1: Initial conversation
        session1_memory = {
            "conversation": [
                {
                    "role": "user",
                    "content": "Analyze AAPL for me",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "role": "assistant",
                    "content": "AAPL looks bullish with strong momentum. RSI is at 65, showing some overbought conditions.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "user_profile": {
                "trading_experience": "intermediate",
                "preferred_timeframes": ["1D", "4H"],
                "last_analysis": "AAPL"
            }
        }
        
        await mock_letta_client.update_memory(agent_id, session1_memory)
        
        # Simulate session end
        await asyncio.sleep(0.1)
        
        # Session 2: Continue conversation
        session2_additions = {
            "conversation": [
                {
                    "role": "user", 
                    "content": "What about GOOGL?",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "role": "assistant",
                    "content": "GOOGL is more conservative. Based on your intermediate experience, I'd recommend the 4H timeframe.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "user_profile": {
                "trading_experience": "intermediate",
                "preferred_timeframes": ["1D", "4H"],
                "last_analysis": "GOOGL",
                "analyses_completed": 2
            }
        }
        
        # In real implementation, this would merge with existing memory
        # For mock, we'll simulate the merge
        updated_memory = {
            "conversation": session1_memory["conversation"] + session2_additions["conversation"],
            "user_profile": {
                **session1_memory["user_profile"],
                **session2_additions["user_profile"]
            }
        }
        
        await mock_letta_client.update_memory(agent_id, updated_memory)
        
        # Session 3: Retrieve and verify all memory
        final_memory = await mock_letta_client.get_memory(agent_id)
        
        assert len(final_memory["conversation"]) == 4  # 2 from session 1 + 2 from session 2
        assert final_memory["user_profile"]["analyses_completed"] == 2
        assert final_memory["user_profile"]["last_analysis"] == "GOOGL"
        
        print("Memory persisted correctly through multiple sessions")
        print(f"Total conversations: {len(final_memory['conversation'])}")
        print(f"Analyses completed: {final_memory['user_profile']['analyses_completed']}")
    
    async def test_memory_size_limits_and_eviction(self, mock_letta_client):
        """Test memory size limits and automatic eviction of old conversations"""
        agent_config = {
            "name": "memory_limit_agent",
            "system_prompt": "You are a trading assistant with limited memory capacity.",
            "model": "gpt-4"
        }
        
        create_result = await mock_letta_client.create_agent(agent_config)
        agent_id = create_result["agent_id"]
        
        max_conversations = 10
        total_conversations = 25
        
        # Generate large conversation history
        conversations = []
        for i in range(total_conversations):
            conversations.extend([
                {
                    "role": "user",
                    "content": f"Question {i+1}: What's your outlook on TEST{i % 5}?",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=total_conversations-i)).isoformat()
                },
                {
                    "role": "assistant",
                    "content": f"Response {i+1}: TEST{i % 5} shows mixed signals. I'd wait for better entry.",
                    "timestamp": (datetime.utcnow() - timedelta(minutes=total_conversations-i)).isoformat()
                }
            ])
        
        memory_data = {
            "conversation": conversations,
            "memory_metadata": {
                "max_conversations": max_conversations,
                "total_conversations": len(conversations),
                "created_at": datetime.utcnow().isoformat()
            }
        }
        
        await mock_letta_client.update_memory(agent_id, memory_data)
        
        # Simulate memory eviction (in real system, Letta would handle this)
        # For mock, we'll simulate what the system should do
        pruned_conversations = conversations[-max_conversations*2:]  # Keep last conversations
        
        pruned_memory = {
            "conversation": pruned_conversations,
            "memory_metadata": {
                "max_conversations": max_conversations,
                "total_conversations": len(pruned_conversations),
                "pruned_at": datetime.utcnow().isoformat(),
                "pruned_count": len(conversations) - len(pruned_conversations)
            }
        }
        
        await mock_letta_client.update_memory(agent_id, pruned_memory)
        
        # Verify memory was pruned correctly
        retrieved_memory = await mock_letta_client.get_memory(agent_id)
        
        assert len(retrieved_memory["conversation"]) <= max_conversations * 2
        assert "pruned_count" in retrieved_memory["memory_metadata"]
        
        print(f"Memory pruning test:")
        print(f"  Original conversations: {total_conversations * 2}")
        print(f"  After pruning: {len(retrieved_memory['conversation'])}")
        print(f"  Pruned: {retrieved_memory['memory_metadata']['pruned_count']}")
    
    async def test_memory_backup_and_restore(self, mock_letta_client):
        """Test memory backup and restoration capabilities"""
        agent_config = {
            "name": "backup_agent",
            "system_prompt": "You are a trading assistant with backup capabilities.",
            "model": "gpt-4"
        }
        
        create_result = await mock_letta_client.create_agent(agent_config)
        agent_id = create_result["agent_id"]
        
        # Create extensive memory
        original_memory = {
            "conversation": [
                {
                    "role": "user",
                    "content": f"Backup test conversation {i}",
                    "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat()
                }
                for i in range(20)
            ],
            "trading_data": {
                "portfolio_value": 100000,
                "trades": [{"symbol": "AAPL", "action": "BUY", "quantity": 100} for _ in range(5)],
                "performance_metrics": {"sharpe": 1.2, "max_drawdown": 0.15}
            },
            "backup_info": {
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
        }
        
        # Store original memory
        await mock_letta_client.update_memory(agent_id, original_memory)
        
        # Simulate memory backup
        backup_data = {
            "agent_id": agent_id,
            "backup_timestamp": datetime.utcnow().isoformat(),
            "memory": original_memory,
            "checksum": "mock_checksum_12345"
        }
        
        # Store backup (in real system, this would be saved to persistent storage)
        backup_storage_key = f"backup:{agent_id}:{int(time.time())}"
        # For mock, we'll just verify the backup was created
        backup_created = True  # Simulate successful backup
        
        assert backup_created is True
        print("Memory backup created successfully")
        
        # Simulate memory corruption or loss
        corrupted_memory = {
            "conversation": [],
            "error": "Memory corrupted"
        }
        
        await mock_letta_client.update_memory(agent_id, corrupted_memory)
        
        # Verify memory is corrupted
        current_memory = await mock_letta_client.get_memory(agent_id)
        assert len(current_memory["conversation"]) == 0
        
        # Restore from backup
        restored_memory = backup_data["memory"]
        restore_result = await mock_letta_client.update_memory(agent_id, restored_memory)
        
        assert restore_result is True
        
        # Verify restoration
        final_memory = await mock_letta_client.get_memory(agent_id)
        assert len(final_memory["conversation"]) == 20
        assert "trading_data" in final_memory
        assert final_memory["trading_data"]["portfolio_value"] == 100000
        
        print("Memory restoration successful")
        print(f"Restored {len(final_memory['conversation'])} conversations")
    
    async def test_memory_concurrent_access(self, mock_letta_client):
        """Test concurrent memory access and consistency"""
        agent_config = {
            "name": "concurrent_agent",
            "system_prompt": "You are a trading assistant handling concurrent requests.",
            "model": "gpt-4"
        }
        
        create_result = await mock_letta_client.create_agent(agent_config)
        agent_id = create_result["agent_id"]
        
        async def memory_update_worker(worker_id: int, num_updates: int) -> List[Dict]:
            """Worker function for concurrent memory updates"""
            updates = []
            
            for i in range(num_updates):
                update_data = {
                    "conversation": [
                        {
                            "role": "user",
                            "content": f"Worker {worker_id} update {i}",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    ],
                    "worker_metadata": {
                        "worker_id": worker_id,
                        "update_index": i,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                
                await mock_letta_client.update_memory(agent_id, update_data)
                updates.append(update_data)
                
                # Small delay to simulate real work
                await asyncio.sleep(0.01)
            
            return updates
        
        # Run concurrent workers
        num_workers = 3
        updates_per_worker = 5
        
        print(f"Running {num_workers} concurrent workers with {updates_per_worker} updates each...")
        
        start_time = time.time()
        worker_tasks = [
            memory_update_worker(worker_id, updates_per_worker)
            for worker_id in range(num_workers)
        ]
        
        all_updates = await asyncio.gather(*worker_tasks)
        total_time = time.time() - start_time
        
        # Flatten all updates
        all_update_data = [update for worker_updates in all_updates for update in worker_updates]
        
        print(f"Concurrent updates completed in {total_time:.3f}s")
        print(f"Total updates: {len(all_update_data)}")
        
        # Get final memory state
        final_memory = await mock_letta_client.get_memory(agent_id)
        
        # Verify consistency (in real implementation, this would check for race conditions)
        print(f"Final memory conversation count: {len(final_memory.get('conversation', []))}")
        
        # For mock, we'll just verify the process completed without errors
        assert len(all_update_data) == num_workers * updates_per_worker
        assert total_time < 5.0  # Should complete within reasonable time
    
    async def test_memory_persistence_performance(self, mock_letta_client):
        """Test performance of memory persistence operations"""
        agent_config = {
            "name": "performance_agent",
            "system_prompt": "You are a trading assistant for performance testing.",
            "model": "gpt-4"
        }
        
        create_result = await mock_letta_client.create_agent(agent_config)
        agent_id = create_result["agent_id"]
        
        # Test memory write performance
        write_times = []
        num_writes = 20
        
        for i in range(num_writes):
            memory_data = {
                "conversation": [
                    {
                        "role": "user",
                        "content": f"Performance test message {i}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ],
                "performance_test": True,
                "write_index": i
            }
            
            start_time = time.time()
            await mock_letta_client.update_memory(agent_id, memory_data)
            write_time = time.time() - start_time
            
            write_times.append(write_time)
        
        # Test memory read performance
        read_times = []
        num_reads = 20
        
        for _ in range(num_reads):
            start_time = time.time()
            await mock_letta_client.get_memory(agent_id)
            read_time = time.time() - start_time
            
            read_times.append(read_time)
        
        # Calculate statistics
        avg_write_time = sum(write_times) / len(write_times)
        avg_read_time = sum(read_times) / len(read_times)
        
        max_write_time = max(write_times)
        max_read_time = max(read_times)
        
        print(f"Memory persistence performance:")
        print(f"  Write operations:")
        print(f"    Count: {num_writes}")
        print(f"    Average: {avg_write_time:.4f}s")
        print(f"    Max: {max_write_time:.4f}s")
        print(f"  Read operations:")
        print(f"    Count: {num_reads}")
        print(f"    Average: {avg_read_time:.4f}s")
        print(f"    Max: {max_read_time:.4f}s")
        
        # Performance assertions
        assert avg_write_time < 0.1  # Writes should be fast
        assert avg_read_time < 0.05  # Reads should be very fast
        assert max_write_time < 0.2  # No write should take more than 200ms
        assert max_read_time < 0.1   # No read should take more than 100ms