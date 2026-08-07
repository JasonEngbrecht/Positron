"""
Driver adapters that present a unified interface over the PS3000a and PS6000
picosdk APIs.

Each driver wraps one open scope handle plus its picosdk module and maps
unified method names onto the series-specific SDK calls. Genuine hardware
differences live INSIDE the drivers and are deliberate:

- PS3000a: 1 MOhm DC coupling, enum-dict range/coupling codes, max/min buffer
  pairs registered per (channel, segment) via ps3000aSetDataBuffers.
- PS6000: 50 Ohm DC coupling (physics choice for PMT pulses - do not "fix"),
  a 7th bandwidth argument to SetChannel, single buffers registered per
  (channel, waveform) via ps6000SetDataBufferBulk.

Do not unify these with a generic name-mangler; the signatures and enum
values differ for real (see docs/picosdk-python-wrappers-master/picosdk/).
"""

import ctypes
from typing import Optional, Protocol, Tuple

import numpy as np

from picosdk.functions import assert_pico_ok
from positron.scope.connection import ScopeInfo


class ScopeDriver(Protocol):
    """Unified low-level operations on an open PicoScope handle."""

    series: str
    voltage_range_code_100mv: int
    default_batch_size: int
    timebase_trial_samples: int

    def set_channel(self, channel_idx: int) -> None: ...
    def get_timebase2(self, timebase: int) -> Optional[Tuple[float, int]]: ...
    def get_unit_info(self, info_type: int) -> str: ...
    def memory_segments(self, num_segments: int, num_samples: int) -> None: ...
    def set_no_of_captures(self, num_captures: int) -> None: ...
    def run_block(self, pre_trigger_samples: int, post_trigger_samples: int,
                  timebase: int) -> None: ...
    def is_ready(self) -> bool: ...
    def get_values_bulk(self, num_samples: int, num_segments: int) -> int: ...
    def register_buffer(self, channel_idx: int, segment: int,
                        buffer_max: np.ndarray, buffer_min: np.ndarray,
                        num_samples: int) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class PS3000aDriver:
    """Driver for PS3000a series scopes (e.g. 3406D MSO)."""

    series = "3000a"
    default_batch_size = 10
    timebase_trial_samples = 500

    def __init__(self, scope_info: ScopeInfo):
        if scope_info.series != self.series:
            raise ValueError(
                f"PS3000aDriver requires series {self.series}, got {scope_info.series}"
            )
        self.scope_info = scope_info
        self.handle = scope_info.handle
        self.ps = scope_info.api_module
        self.voltage_range_code_100mv = self.ps.PS3000A_RANGE['PS3000A_100MV']

    def set_channel(self, channel_idx: int) -> None:
        """Enable a channel: 100 mV range, DC coupling (1 MOhm), 0 V offset."""
        status = self.ps.ps3000aSetChannel(
            self.handle,
            channel_idx,
            1,  # enabled
            self.ps.PS3000A_COUPLING['PS3000A_DC'],
            self.voltage_range_code_100mv,
            0.0  # analog offset
        )
        assert_pico_ok(status)

    def get_timebase2(self, timebase: int) -> Optional[Tuple[float, int]]:
        """
        Query a timebase index.

        Returns:
            (sample_interval_ns, max_samples) if the timebase is valid with
            the current channel configuration, None otherwise.
        """
        time_interval_ns = ctypes.c_float()
        max_samples = ctypes.c_int32()
        status = self.ps.ps3000aGetTimebase2(
            self.handle,
            timebase,
            self.timebase_trial_samples,
            ctypes.byref(time_interval_ns),
            1,  # oversample (not used)
            ctypes.byref(max_samples),
            0  # segment index
        )
        if status != 0:  # not PICO_OK
            return None
        return (time_interval_ns.value, max_samples.value)

    def get_unit_info(self, info_type: int) -> str:
        """Get a unit info string (3 = variant/model, 4 = serial number)."""
        info_buffer = ctypes.create_string_buffer(256)
        info_string = ctypes.cast(info_buffer, ctypes.c_char_p)
        required_size = ctypes.c_int16(256)
        status = self.ps.ps3000aGetUnitInfo(
            self.handle, info_string, 256, ctypes.byref(required_size), info_type
        )
        try:
            assert_pico_ok(status)
            return info_buffer.value.decode('utf-8')
        except Exception:
            return "Unknown"

    def memory_segments(self, num_segments: int, num_samples: int) -> None:
        max_samples = ctypes.c_int32(num_samples)
        status = self.ps.ps3000aMemorySegments(
            self.handle, num_segments, ctypes.byref(max_samples)
        )
        assert_pico_ok(status)

    def set_no_of_captures(self, num_captures: int) -> None:
        status = self.ps.ps3000aSetNoOfCaptures(self.handle, num_captures)
        assert_pico_ok(status)

    def run_block(self, pre_trigger_samples: int, post_trigger_samples: int,
                  timebase: int) -> None:
        status = self.ps.ps3000aRunBlock(
            self.handle,
            ctypes.c_int32(pre_trigger_samples),
            ctypes.c_int32(post_trigger_samples),
            ctypes.c_uint32(timebase),
            ctypes.c_int16(1),  # oversample (not used)
            None,  # time indisposed
            ctypes.c_uint32(0),  # segment index (0 for rapid block)
            None,  # lpReady callback
            None  # pParameter
        )
        assert_pico_ok(status)

    def is_ready(self) -> bool:
        ready = ctypes.c_int16(0)
        self.ps.ps3000aIsReady(self.handle, ctypes.byref(ready))
        return ready.value != 0

    def get_values_bulk(self, num_samples: int, num_segments: int) -> int:
        """
        Download all segments into the registered buffers.

        Returns the actual number of samples retrieved per segment. The
        overflow array is required by the API; per-segment overflow flags
        are currently not inspected.
        """
        overflow = (ctypes.c_int16 * num_segments)()
        c_num_samples = ctypes.c_int32(num_samples)
        status = self.ps.ps3000aGetValuesBulk(
            self.handle,
            ctypes.byref(c_num_samples),
            ctypes.c_uint32(0),  # from segment
            ctypes.c_uint32(num_segments - 1),  # to segment
            ctypes.c_uint32(1),  # downsample ratio
            ctypes.c_int32(0),  # downsample ratio mode (none)
            ctypes.byref(overflow)
        )
        assert_pico_ok(status)
        return c_num_samples.value

    def register_buffer(self, channel_idx: int, segment: int,
                        buffer_max: np.ndarray, buffer_min: np.ndarray,
                        num_samples: int) -> None:
        """Register a max/min buffer pair for one (channel, segment)."""
        status = self.ps.ps3000aSetDataBuffers(
            self.handle,
            channel_idx,
            buffer_max.ctypes.data,
            buffer_min.ctypes.data,
            num_samples,
            segment,
            0  # PS3000A_RATIO_MODE_NONE
        )
        assert_pico_ok(status)

    def stop(self) -> None:
        status = self.ps.ps3000aStop(self.handle)
        assert_pico_ok(status)

    def close(self) -> None:
        status = self.ps.ps3000aCloseUnit(self.handle)
        assert_pico_ok(status)


class PS6000Driver:
    """Driver for PS6000 series scopes (original ps6000 API, e.g. 6402D)."""

    series = "6000"
    default_batch_size = 20
    timebase_trial_samples = 1000

    # PS6000_RANGE index 3 = 100 mV (see docs/picosdk-python-wrappers-master)
    voltage_range_code_100mv = 3

    def __init__(self, scope_info: ScopeInfo):
        if scope_info.series != self.series:
            raise ValueError(
                f"PS6000Driver requires series {self.series}, got {scope_info.series}"
            )
        self.scope_info = scope_info
        self.handle = scope_info.handle
        self.ps = scope_info.api_module

    def set_channel(self, channel_idx: int) -> None:
        """
        Enable a channel: 100 mV range, DC 50 Ohm coupling, full bandwidth.

        The 50 Ohm input termination (PS6000_DC_50R = 2) is a deliberate
        physics choice for fast PMT pulses.
        """
        status = self.ps.ps6000SetChannel(
            self.handle,
            channel_idx,
            1,  # enabled
            2,  # PS6000_DC_50R
            self.voltage_range_code_100mv,
            0.0,  # analog offset
            0  # PS6000_BW_FULL
        )
        assert_pico_ok(status)

    def get_timebase2(self, timebase: int) -> Optional[Tuple[float, int]]:
        """
        Query a timebase index.

        Returns:
            (sample_interval_ns, max_samples) if the timebase is valid with
            the current channel configuration, None otherwise.
        """
        time_interval_ns = ctypes.c_float()
        max_samples = ctypes.c_int32()
        status = self.ps.ps6000GetTimebase2(
            self.handle,
            timebase,
            self.timebase_trial_samples,
            ctypes.byref(time_interval_ns),
            1,  # oversample (not used)
            ctypes.byref(max_samples),
            0  # segment index
        )
        if status != 0:  # not PICO_OK
            return None
        return (time_interval_ns.value, max_samples.value)

    def get_unit_info(self, info_type: int) -> str:
        """Get a unit info string (3 = variant/model, 4 = serial number)."""
        info_buffer = ctypes.create_string_buffer(256)
        info_string = ctypes.cast(info_buffer, ctypes.c_char_p)
        required_size = ctypes.c_int16(256)
        status = self.ps.ps6000GetUnitInfo(
            self.handle, info_string, 256, ctypes.byref(required_size), info_type
        )
        try:
            assert_pico_ok(status)
            return info_buffer.value.decode('utf-8')
        except Exception:
            return "Unknown"

    def memory_segments(self, num_segments: int, num_samples: int) -> None:
        max_samples = ctypes.c_int32(num_samples)
        status = self.ps.ps6000MemorySegments(
            self.handle, num_segments, ctypes.byref(max_samples)
        )
        assert_pico_ok(status)

    def set_no_of_captures(self, num_captures: int) -> None:
        status = self.ps.ps6000SetNoOfCaptures(self.handle, num_captures)
        assert_pico_ok(status)

    def run_block(self, pre_trigger_samples: int, post_trigger_samples: int,
                  timebase: int) -> None:
        time_indisposed_ms = ctypes.c_int32(0)
        status = self.ps.ps6000RunBlock(
            self.handle,
            pre_trigger_samples,
            post_trigger_samples,
            timebase,
            1,  # oversample (not used)
            ctypes.byref(time_indisposed_ms),
            0,  # segment index (0 for rapid block)
            None,  # lpReady callback
            None  # pParameter
        )
        assert_pico_ok(status)

    def is_ready(self) -> bool:
        ready = ctypes.c_int16(0)
        self.ps.ps6000IsReady(self.handle, ctypes.byref(ready))
        return ready.value != 0

    def get_values_bulk(self, num_samples: int, num_segments: int) -> int:
        """
        Download all segments into the registered buffers.

        Returns the actual number of samples retrieved per segment. The
        overflow array is required by the API; per-segment overflow flags
        are currently not inspected.
        """
        overflow = (ctypes.c_int16 * num_segments)()
        c_num_samples = ctypes.c_int32(num_samples)
        status = self.ps.ps6000GetValuesBulk(
            self.handle,
            ctypes.byref(c_num_samples),
            0,  # from segment
            num_segments - 1,  # to segment
            1,  # downsample ratio
            0,  # PS6000_RATIO_MODE_NONE
            ctypes.byref(overflow)
        )
        assert_pico_ok(status)
        return c_num_samples.value

    def register_buffer(self, channel_idx: int, segment: int,
                        buffer_max: np.ndarray, buffer_min: np.ndarray,
                        num_samples: int) -> None:
        """
        Register a buffer for one (channel, waveform index).

        The ps6000 rapid-block API takes a single buffer per waveform
        (no max/min pair); buffer_min is accepted for interface parity
        but not registered.
        """
        status = self.ps.ps6000SetDataBufferBulk(
            self.handle,
            channel_idx,
            buffer_max.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
            num_samples,
            segment,  # waveform index
            0  # PS6000_RATIO_MODE_NONE
        )
        assert_pico_ok(status)

    def stop(self) -> None:
        status = self.ps.ps6000Stop(self.handle)
        assert_pico_ok(status)

    def close(self) -> None:
        status = self.ps.ps6000CloseUnit(self.handle)
        assert_pico_ok(status)


def create_driver(scope_info: ScopeInfo) -> ScopeDriver:
    """
    Factory: create the appropriate driver for a connected scope.

    Args:
        scope_info: Information about the connected scope

    Returns:
        Driver instance wrapping the scope's handle and SDK module

    Raises:
        ValueError: If the scope series is not supported
    """
    if scope_info.series == "3000a":
        return PS3000aDriver(scope_info)
    elif scope_info.series == "6000":
        return PS6000Driver(scope_info)
    else:
        raise ValueError(
            f"Unsupported scope series: {scope_info.series}. "
            f"Supported series: 3000a, 6000"
        )
