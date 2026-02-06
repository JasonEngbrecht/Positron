"""
Complete test for PS6000 implementation with 6402D.
Tests connection, configuration, and trigger setup.
"""

import sys
from positron.scope.connection import detect_and_connect, disconnect
from positron.scope.configuration import create_configurator
from positron.scope.trigger import create_trigger_configurator
from positron.config import TriggerConfig, TriggerCondition

def test_ps6000_complete():
    """Test PS6000 connection, configuration, and trigger setup."""
    print("PS6000 Complete Test for 6402D")
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
        print(f"   - Timebase Index: {timebase_info.timebase_index}")
        
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        disconnect()
        return 1
    
    # Test 3: Trigger Configuration
    print("\n3. Testing trigger configuration...")
    try:
        # Create a simple trigger config - trigger on any channel (OR logic)
        trigger_config = TriggerConfig(
            condition_1=TriggerCondition(enabled=True, channels=['A', 'B', 'C', 'D']),
            auto_trigger_enabled=True
        )
        
        trigger_configurator = create_trigger_configurator(scope_info)
        trigger_info = trigger_configurator.apply_trigger(trigger_config)
        
        print("   [OK] Trigger configured")
        print(f"\n   Trigger Details:")
        print(f"   - Threshold: {trigger_info.threshold_mv} mV")
        print(f"   - Direction: {trigger_info.direction}")
        print(f"   - Auto-trigger: {trigger_info.auto_trigger_ms} ms")
        print(f"   - Conditions: {trigger_info.num_conditions}")
        for summary in trigger_info.conditions_summary:
            print(f"     * {summary}")
        
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        disconnect()
        return 1
    
    # Cleanup
    print("\n4. Disconnecting...")
    disconnect()
    print("   [OK] Disconnected")
    
    print("\n" + "=" * 60)
    print("SUCCESS! PS6000 implementation is working!")
    print("=" * 60)
    print("\nThe PS6000 (6402D) is now integrated into Positron.")
    print("You can run the main application: python main.py")
    return 0

if __name__ == "__main__":
    sys.exit(test_ps6000_complete())
