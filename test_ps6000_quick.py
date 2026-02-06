"""
Quick test for PS6000 implementation with 6402D.
Tests connection and configuration only.
"""

import sys
from positron.scope.connection import detect_and_connect, disconnect
from positron.scope.configuration import create_configurator

def test_ps6000():
    """Test PS6000 connection and configuration."""
    print("PS6000 Quick Test for 6402D")
    print("=" * 60)
    
    # Test 1: Connection
    print("\n1. Testing connection...")
    try:
        scope_info = detect_and_connect()
        print(f"   [OK] Connected")
        print(f"   Series: {scope_info.series}")
        print(f"   Model: {scope_info.variant}")
        print(f"   Serial: {scope_info.serial}")
        print(f"   Max ADC: {scope_info.max_adc}")
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 2: Configuration
    print("\n2. Testing configuration...")
    try:
        configurator = create_configurator(scope_info)
        configurator.apply_configuration()
        print("   [OK] Configuration applied")
        
        timebase_info = configurator.get_timebase_info()
        print(f"\n   Configuration Details:")
        print(f"   - Sample Rate: {timebase_info.sample_rate_hz / 1e6:.1f} MS/s")
        print(f"   - Sample Interval: {timebase_info.sample_interval_ns:.2f} ns")
        print(f"   - Total Samples: {timebase_info.total_samples}")
        print(f"   - Pre-trigger: {timebase_info.pre_trigger_samples}")
        print(f"   - Voltage Range: 100 mV (code {timebase_info.voltage_range_code})")
        print(f"   - Resolution: 8-bit (fixed)")
        print(f"   - Impedance: 1 MOhm (fixed)")
        
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        disconnect()
        return 1
    
    # Cleanup
    print("\n3. Disconnecting...")
    disconnect()
    print("   [OK] Disconnected")
    
    print("\n" + "=" * 60)
    print("SUCCESS! PS6000 support is working!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(test_ps6000())
