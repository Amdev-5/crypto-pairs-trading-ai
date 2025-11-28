#!/usr/bin/env python3
"""Performance analysis script for trading engine"""

import re
from collections import defaultdict
from datetime import datetime

def analyze_performance(log_file='logs/trading.log'):
    """Analyze trading engine performance metrics"""
    
    loop_times = []
    execution_times = []
    position_durations = []
    
    with open(log_file, 'r') as f:
        for line in f:
            # Extract loop times
            if 'Loop time:' in line:
                match = re.search(r'Loop time: ([\d.]+)s', line)
                if match:
                    loop_times.append(float(match.group(1)))
            
            # Extract position durations
            if 'Duration:' in line and 'Position closed' in line:
                match = re.search(r'Duration: ([\d.]+)m', line)
                if match:
                    position_durations.append(float(match.group(1)))
    
    print("=" * 60)
    print("TRADING ENGINE PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    if loop_times:
        print(f"\n📊 LOOP LATENCY (Main Loop Speed)")
        print(f"   Average: {sum(loop_times)/len(loop_times):.3f}s")
        print(f"   Min: {min(loop_times):.3f}s")
        print(f"   Max: {max(loop_times):.3f}s")
        print(f"   Total iterations: {len(loop_times)}")
        print(f"   Target: <1s (HFT), <5s (Medium Freq)")
        
        if sum(loop_times)/len(loop_times) < 1.0:
            print(f"   ✅ EXCELLENT - HFT speed achieved!")
        elif sum(loop_times)/len(loop_times) < 5.0:
            print(f"   ✅ GOOD - Medium frequency speed")
        else:
            print(f"   ⚠️  SLOW - Consider optimization")
    
    if position_durations:
        print(f"\n⏱️  POSITION HOLDING TIME")
        print(f"   Average: {sum(position_durations)/len(position_durations):.1f} minutes")
        print(f"   Min: {min(position_durations):.1f} minutes")
        print(f"   Max: {max(position_durations):.1f} minutes")
        print(f"   Total closed trades: {len(position_durations)}")
    else:
        print(f"\n⏱️  POSITION HOLDING TIME")
        print(f"   No closed trades yet")
    
    # Check data source
    with open(log_file, 'r') as f:
        content = f.read()
        websocket_fallbacks = content.count('WebSocket prices not available')
        total_executions = content.count('Executing')
        
        print(f"\n📡 DATA SOURCE")
        if total_executions > 0:
            websocket_usage = ((total_executions - websocket_fallbacks) / total_executions) * 100
            print(f"   WebSocket: {websocket_usage:.1f}%")
            print(f"   REST API Fallback: {100-websocket_usage:.1f}%")
            
            if websocket_usage > 90:
                print(f"   ✅ EXCELLENT - Real-time data")
            elif websocket_usage > 50:
                print(f"   ⚠️  MODERATE - Some delays")
            else:
                print(f"   ❌ POOR - Too many REST API calls")
        else:
            print(f"   No executions attempted yet")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    analyze_performance()
