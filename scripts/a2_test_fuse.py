"""
A2: 累计 token 熔断测试
用极低上限验证熔断机制能正确触发并输出信息。
"""
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts' / 'llm'))
from client import LLMClient, TokenBudgetExceededError


def test_input_fuse():
    """Test that input token budget fuse trips correctly."""
    print("=" * 60)
    print("TEST 1: Input Token Fuse")
    print("=" * 60)

    # Set very low input limit
    client = LLMClient(profile='mock', run_id='a2_fuse_test_input')
    client.logger.max_input_tokens = 1000

    success = False
    for i in range(10):
        try:
            client.chat(
                messages=[{'role': 'user', 'content': 'x' * 5000}],  # ~1666 estimated tokens
                task_name='fuse_test_input',
                input_volume='test',
            )
        except TokenBudgetExceededError as e:
            print(f"  ✓ Fuse tripped: {e.direction}")
            print(f"    Current total: {e.current_total:,}")
            print(f"    Limit: {e.limit:,}")
            if e.current_total <= e.limit:
                print(f"    ✓ Fuse tripped BEFORE exceeding limit (pre-flight check)")
            success = True
            break
        except Exception as e:
            print(f"  Unexpected error: {type(e).__name__}: {e}")

    if not success:
        print("  ✗ Fuse did NOT trip as expected!")
    print()
    return success


def test_output_fuse():
    """Test that output token budget fuse trips correctly."""
    print("=" * 60)
    print("TEST 2: Output Token Fuse")
    print("=" * 60)

    client = LLMClient(profile='mock', run_id='a2_fuse_test_output')
    client.logger.max_output_tokens = 100

    success = False
    for i in range(5):
        try:
            # mock_response will generate ~333 estimated output tokens (1000 chars / 3)
            client.chat(
                messages=[{'role': 'user', 'content': 'test'}],
                task_name='fuse_test_output',
                input_volume='test',
                mock_response='A' * 1000,  # ~333 estimated output tokens
            )
        except TokenBudgetExceededError as e:
            print(f"  ✓ Fuse tripped: {e.direction}")
            print(f"    Current total: {e.current_total:,}")
            print(f"    Limit: {e.limit:,}")
            success = True
            break
        except Exception as e:
            print(f"  Unexpected error: {type(e).__name__}: {e}")

    if not success:
        print("  ✗ Fuse did NOT trip as expected!")
    print()
    return success


def test_fuse_message_contains_chunks():
    """Test that fuse error message includes completed chunks."""
    print("=" * 60)
    print("TEST 3: Fuse Error Message Includes Completed Chunks")
    print("=" * 60)

    client = LLMClient(profile='mock', run_id='a2_fuse_test_chunks')
    client.logger.max_input_tokens = 500
    client.logger.mark_chunk_completed('C001')
    client.logger.mark_chunk_completed('C002')

    try:
        client.chat(
            messages=[{'role': 'user', 'content': 'x' * 5000}],
            task_name='fuse_test_chunks',
            input_volume='test',
        )
    except TokenBudgetExceededError as e:
        msg = str(e)
        if 'C001' in msg or 'C002' in msg:
            print(f"  ✓ Error message includes completed chunks")
            print(f"  Message excerpt: {msg[:200]}...")
        else:
            print(f"  ✗ Error message does NOT include chunk info")
            print(f"  Full message: {msg}")
            return False
    except Exception as e:
        print(f"  Unexpected error: {type(e).__name__}: {e}")
        return False

    print()
    return True


def main():
    results = []
    results.append(('Input fuse', test_input_fuse()))
    results.append(('Output fuse', test_output_fuse()))
    results.append(('Chunk info in message', test_fuse_message_contains_chunks()))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = 'PASS' if passed else 'FAIL'
        print(f"  [{status}] {name}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n✓ All fuse tests passed.")
    else:
        print("\n✗ Some fuse tests FAILED.")

    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
