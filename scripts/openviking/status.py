"""
OpenViking 状态查询
查询库内文件数、目录结构、当前计费档位与累计时长
"""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def query_status():
    api_key = os.environ.get('ARK_API_KEY', '')
    if not api_key:
        print("ARK_API_KEY not set. Cannot query live status.")
        print("Set ARK_API_KEY and retry.")
        return

    # TODO: Actual OpenViking API call to query library status
    # GET {endpoint}/libraries/{library_id}/status
    # Returns: file_count, directory_tree, billing_tier, accumulated_hours

    print("Status query not yet implemented (requires live API key).")
    print("Library ID: ov-290dce6904ec3189")
    print("Endpoint: https://api.vikingdb.cn-beijing.volces.com/openviking")

if __name__ == '__main__':
    query_status()