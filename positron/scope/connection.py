"""
Scope discovery and connection management for PicoScope 3000a and 6000a series.

This module handles automatic detection and connection to PicoScope oscilloscopes,
supporting both PS3000a and PS6000a series devices.
"""

import ctypes
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from picosdk.errors import DeviceNotFoundError, PicoSDKCtypesError
from picosdk.functions import assert_pico_ok


@dataclass
class ScopeInfo:
    """Information about a connected oscilloscope."""
    series: str  # "3000a" or "6000a"
    variant: str  # e.g., "3406D MSO"
    serial: str
    handle: ctypes.c_int16
    max_adc: int  # Maximum ADC count for voltage conversion
    api_module: Any  # Reference to ps3000a or ps6000a module


class ScopeConnection:
    """
    Manages connection to PicoScope oscilloscopes with automatic series detection.
    """
    
    def __init__(self):
        """Initialize scope connection manager."""
        self._scope_info: Optional[ScopeInfo] = None
        self._ps3000a = None
        self._ps6000 = None
    
    @property
    def is_connected(self) -> bool:
        """Check if a scope is currently connected."""
        return self._scope_info is not None
    
    @property
    def scope_info(self) -> Optional[ScopeInfo]:
        """Get information about the connected scope."""
        return self._scope_info
    
    def detect_and_connect(self) -> ScopeInfo:
        """
        Automatically detect and connect to a PicoScope device.
        
        Tries PS6000 series first, then PS3000a series.
        
        Returns:
            ScopeInfo: Information about the connected device
            
        Raises:
            DeviceNotFoundError: If no compatible device is found
            PicoSDKCtypesError: If there's an error communicating with the device
        """
        # Try PS6000 first (6402D)
        try:
            scope_info = self._connect_ps6000()
            self._scope_info = scope_info
            return scope_info
        except (DeviceNotFoundError, PicoSDKCtypesError, Exception) as e:
            # Not a PS6000 device or not found
            pass
        
        # Try PS3000a as fallback
        try:
            scope_info = self._connect_ps3000a()
            self._scope_info = scope_info
            return scope_info
        except (DeviceNotFoundError, PicoSDKCtypesError, Exception) as e:
            # Not a PS3000a device or not found
            pass
        
        raise DeviceNotFoundError(
            "No PicoScope device found. Please check:\n"
            "- Device is connected via USB\n"
            "- PicoScope drivers are installed\n"
            "- Device is not in use by another application"
        )
    
    def _connect_ps3000a(self) -> ScopeInfo:
        """
        Connect to a PS3000a series oscilloscope.
        
        Returns:
            ScopeInfo: Information about the connected device
            
        Raises:
            DeviceNotFoundError: If no PS3000a device is found
        """
        from picosdk.ps3000a import ps3000a as ps
        self._ps3000a = ps
        
        # Create handle
        chandle = ctypes.c_int16()
        status = {}
        
        # Try to open the device
        status["openunit"] = ps.ps3000aOpenUnit(ctypes.byref(chandle), None)
        
        # Handle power state errors (common with USB-powered scopes)
        powerstate = status["openunit"]
        
        # PICO_POWER_SUPPLY_NOT_CONNECTED = 282
        if powerstate == 282:
            status["ChangePowerSource"] = ps.ps3000aChangePowerSource(chandle, 282)
            assert_pico_ok(status["ChangePowerSource"])
        # PICO_USB3_0_DEVICE_NON_USB3_0_PORT = 286
        elif powerstate == 286:
            status["ChangePowerSource"] = ps.ps3000aChangePowerSource(chandle, 286)
            assert_pico_ok(status["ChangePowerSource"])
        # PICO_OK = 0 or other success codes
        elif powerstate != 0:
            raise DeviceNotFoundError(f"Failed to open PS3000a device (status: {powerstate})")
        
        # Get device information
        variant_str = self._get_unit_info_ps3000a(chandle, ps, 3)  # Variant info (Model)
        serial_str = self._get_unit_info_ps3000a(chandle, ps, 4)  # Serial number
        
        # Get max ADC value
        max_adc = ctypes.c_int16()
        status["maximumValue"] = ps.ps3000aMaximumValue(chandle, ctypes.byref(max_adc))
        assert_pico_ok(status["maximumValue"])
        
        return ScopeInfo(
            series="3000a",
            variant=variant_str,
            serial=serial_str,
            handle=chandle,
            max_adc=max_adc.value,
            api_module=ps
        )
    
    def _connect_ps6000(self) -> ScopeInfo:
        """
        Connect to a PS6000 series oscilloscope (original, not PS6000a).
        
        Returns:
            ScopeInfo: Information about the connected device
            
        Raises:
            DeviceNotFoundError: If no PS6000 device is found
        """
        from picosdk.ps6000 import ps6000 as ps
        
        self._ps6000 = ps
        
        # Create handle
        chandle = ctypes.c_int16()
        status = {}
        
        # Open unit (no resolution parameter for PS6000)
        status["openunit"] = ps.ps6000OpenUnit(ctypes.byref(chandle), None)
        
        try:
            assert_pico_ok(status["openunit"])
        except Exception as e:
            raise DeviceNotFoundError(f"Failed to open PS6000 device: {e}")
        
        # Get device information
        variant_str = self._get_unit_info_ps6000(chandle, ps, 3)  # Variant info (Model)
        serial_str = self._get_unit_info_ps6000(chandle, ps, 4)  # Serial number
        
        # PS6000 uses fixed 8-bit resolution with max ADC value of 32512
        # (This is the value used in official PicoSDK examples)
        max_adc = 32512
        
        return ScopeInfo(
            series="6000",
            variant=variant_str,
            serial=serial_str,
            handle=chandle,
            max_adc=max_adc,
            api_module=ps
        )
    
    def _get_unit_info_ps3000a(self, chandle: ctypes.c_int16, ps, info_type: int) -> str:
        """
        Get unit information string for PS3000a.
        
        Args:
            chandle: Device handle
            ps: ps3000a module
            info_type: Type of information to retrieve
                3 = Variant/Model
                4 = Serial number
                
        Returns:
            Information string
        """
        info_buffer = ctypes.create_string_buffer(256)
        info_string = ctypes.cast(info_buffer, ctypes.c_char_p)
        required_size = ctypes.c_int16(256)
        
        status = ps.ps3000aGetUnitInfo(
            chandle,
            info_string,
            256,
            ctypes.byref(required_size),
            info_type
        )
        
        try:
            assert_pico_ok(status)
            return info_buffer.value.decode('utf-8')
        except Exception:
            return "Unknown"
    
    def _get_unit_info_ps6000(self, chandle: ctypes.c_int16, ps, info_type: int) -> str:
        """
        Get unit information string for PS6000.
        
        Args:
            chandle: Device handle
            ps: ps6000 module
            info_type: Type of information to retrieve
                3 = Variant/Model
                4 = Serial number
                
        Returns:
            Information string
        """
        info_buffer = ctypes.create_string_buffer(256)
        info_string = ctypes.cast(info_buffer, ctypes.c_char_p)
        required_size = ctypes.c_int16(256)
        
        status = ps.ps6000GetUnitInfo(
            chandle,
            info_string,
            256,
            ctypes.byref(required_size),
            info_type
        )
        
        try:
            assert_pico_ok(status)
            return info_buffer.value.decode('utf-8')
        except Exception:
            return "Unknown"
    
    def disconnect(self) -> None:
        """
        Disconnect from the currently connected scope and clean up resources.
        """
        if not self._scope_info:
            return
        
        try:
            if self._scope_info.series == "3000a" and self._ps3000a:
                # Stop any ongoing operations
                try:
                    self._ps3000a.ps3000aStop(self._scope_info.handle)
                except Exception:
                    pass  # Ignore errors if scope wasn't running
                
                # Close the unit
                status = self._ps3000a.ps3000aCloseUnit(self._scope_info.handle)
                try:
                    assert_pico_ok(status)
                except Exception:
                    pass  # Ignore close errors
                    
            elif self._scope_info.series == "6000" and self._ps6000:
                # Stop any ongoing operations
                try:
                    self._ps6000.ps6000Stop(self._scope_info.handle)
                except Exception:
                    pass  # Ignore errors if scope wasn't running
                
                # Close the unit
                status = self._ps6000.ps6000CloseUnit(self._scope_info.handle)
                try:
                    assert_pico_ok(status)
                except Exception:
                    pass  # Ignore close errors
        
        finally:
            # Clear connection state
            self._scope_info = None
            self._ps3000a = None
            self._ps6000 = None


# Global instance for application-wide scope connection
_global_connection: Optional[ScopeConnection] = None


def get_connection() -> ScopeConnection:
    """
    Get the global scope connection instance.
    
    Returns:
        ScopeConnection: The global connection manager
    """
    global _global_connection
    if _global_connection is None:
        _global_connection = ScopeConnection()
    return _global_connection


def detect_and_connect() -> ScopeInfo:
    """
    Convenience function to detect and connect to a scope using the global connection.
    
    Returns:
        ScopeInfo: Information about the connected device
        
    Raises:
        DeviceNotFoundError: If no compatible device is found
    """
    return get_connection().detect_and_connect()


def disconnect() -> None:
    """
    Convenience function to disconnect using the global connection.
    """
    if _global_connection:
        _global_connection.disconnect()


def is_connected() -> bool:
    """
    Check if a scope is currently connected via the global connection.
    
    Returns:
        bool: True if connected, False otherwise
    """
    if _global_connection:
        return _global_connection.is_connected
    return False


def get_scope_info() -> Optional[ScopeInfo]:
    """
    Get information about the currently connected scope.
    
    Returns:
        ScopeInfo or None: Scope information if connected, None otherwise
    """
    if _global_connection:
        return _global_connection.scope_info
    return None
