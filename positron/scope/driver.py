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
from typing import List, Optional, Protocol, Tuple

import numpy as np

from picosdk.functions import assert_pico_ok, mV2adc
from positron.scope.connection import ScopeInfo


# Channel name to index mapping (same on both series)
CHANNEL_MAP = {'A': 0, 'B': 1, 'C': 2, 'D': 3}


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
    def get_no_of_captures(self) -> int: ...
    def register_buffer(self, channel_idx: int, segment: int,
                        buffer_max: np.ndarray, buffer_min: np.ndarray,
                        num_samples: int) -> None: ...
    def set_trigger_properties(self, channels: List[str], threshold_mv: float,
                               hysteresis: int, auto_trigger_ms: int) -> None: ...
    def set_trigger_conditions(self, condition_channel_lists: List[List[str]]) -> None: ...
    def set_trigger_directions(self, channels: List[str]) -> None: ...
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

    def set_trigger_properties(self, channels: List[str], threshold_mv: float,
                               hysteresis: int, auto_trigger_ms: int) -> None:
        """
        Set trigger threshold/hysteresis properties for participating channels.

        Struct field names (thresholdUpperHysteresis etc.) are specific to the
        PS3000a API - verified against the vendored picosdk source.
        """
        max_adc_ctypes = ctypes.c_int16(self.scope_info.max_adc)
        threshold_adc = mV2adc(threshold_mv, self.voltage_range_code_100mv, max_adc_ctypes)

        properties_array = (self.ps.PS3000A_TRIGGER_CHANNEL_PROPERTIES * len(channels))()
        for i, channel_name in enumerate(channels):
            properties_array[i].thresholdUpper = threshold_adc
            properties_array[i].thresholdUpperHysteresis = hysteresis
            properties_array[i].thresholdLower = threshold_adc
            properties_array[i].thresholdLowerHysteresis = hysteresis
            properties_array[i].channel = self.ps.PS3000A_CHANNEL[f"PS3000A_CHANNEL_{channel_name}"]
            properties_array[i].thresholdMode = self.ps.PS3000A_THRESHOLD_MODE["PS3000A_LEVEL"]

        status = self.ps.ps3000aSetTriggerChannelProperties(
            self.handle,
            ctypes.byref(properties_array),
            len(channels),
            0,  # auxOutputEnabled (not used)
            auto_trigger_ms
        )
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger properties: {e}")

    def set_trigger_conditions(self, condition_channel_lists: List[List[str]]) -> None:
        """
        Set trigger conditions: OR logic between condition structs, AND logic
        between the channels within each struct.
        """
        dont_care = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_DONT_CARE"]
        cond_true = self.ps.PS3000A_TRIGGER_STATE["PS3000A_CONDITION_TRUE"]

        conditions_array = (self.ps.PS3000A_TRIGGER_CONDITIONS_V2 * len(condition_channel_lists))()
        for i, channel_names in enumerate(condition_channel_lists):
            conditions_array[i].channelA = dont_care
            conditions_array[i].channelB = dont_care
            conditions_array[i].channelC = dont_care
            conditions_array[i].channelD = dont_care
            conditions_array[i].external = dont_care
            conditions_array[i].aux = dont_care
            conditions_array[i].pulseWidthQualifier = dont_care
            conditions_array[i].digital = dont_care

            for channel_name in channel_names:
                setattr(conditions_array[i], f"channel{channel_name}", cond_true)

        status = self.ps.ps3000aSetTriggerChannelConditionsV2(
            self.handle,
            ctypes.byref(conditions_array),
            len(condition_channel_lists)
        )
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger conditions: {e}")

    def set_trigger_directions(self, channels: List[str]) -> None:
        """Set falling-edge direction for participating channels, NONE elsewhere."""
        none_dir = self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_NONE"]
        falling = self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_FALLING"]

        directions = {name: (falling if name in channels else none_dir)
                      for name in ('A', 'B', 'C', 'D')}

        # Note: External must be set to a valid direction (not NONE) even if not used
        status = self.ps.ps3000aSetTriggerChannelDirections(
            self.handle,
            directions['A'],
            directions['B'],
            directions['C'],
            directions['D'],
            self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_RISING"],  # external
            self.ps.PS3000A_THRESHOLD_DIRECTION["PS3000A_NONE"]  # aux
        )
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger directions: {e}")

    def get_no_of_captures(self) -> int:
        """
        Number of completed rapid-block captures. Valid after run_block
        finished, or after stop() interrupted it (partial batch).
        """
        n = ctypes.c_uint32(0)
        status = self.ps.ps3000aGetNoOfCaptures(self.handle, ctypes.byref(n))
        assert_pico_ok(status)
        return n.value

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

    def set_trigger_properties(self, channels: List[str], threshold_mv: float,
                               hysteresis: int, auto_trigger_ms: int) -> None:
        """
        Set trigger threshold/hysteresis properties for participating channels.

        Struct field names (hysteresisUpper etc.) differ from the PS3000a API
        for real - verified against the vendored picosdk source.
        """
        max_adc_ctypes = ctypes.c_int16(self.scope_info.max_adc)
        threshold_adc = mV2adc(threshold_mv, self.voltage_range_code_100mv, max_adc_ctypes)

        properties_array = (self.ps.PS6000_TRIGGER_CHANNEL_PROPERTIES * len(channels))()
        for i, channel_name in enumerate(channels):
            properties_array[i].thresholdUpper = threshold_adc
            properties_array[i].hysteresisUpper = hysteresis
            properties_array[i].thresholdLower = threshold_adc
            properties_array[i].hysteresisLower = hysteresis
            properties_array[i].channel = CHANNEL_MAP[channel_name]  # numeric codes
            properties_array[i].thresholdMode = 0  # PS6000_LEVEL

        status = self.ps.ps6000SetTriggerChannelProperties(
            self.handle,
            ctypes.byref(properties_array),
            len(channels),
            0,  # auxOutputEnabled (not used)
            auto_trigger_ms
        )
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger properties: {e}")

    def set_trigger_conditions(self, condition_channel_lists: List[List[str]]) -> None:
        """
        Set trigger conditions: OR logic between condition structs, AND logic
        between the channels within each struct.
        """
        # PS6000_CONDITION_DONT_CARE = 0, PS6000_CONDITION_TRUE = 1
        conditions_array = (self.ps.PS6000_TRIGGER_CONDITIONS * len(condition_channel_lists))()
        for i, channel_names in enumerate(condition_channel_lists):
            conditions_array[i].channelA = 0
            conditions_array[i].channelB = 0
            conditions_array[i].channelC = 0
            conditions_array[i].channelD = 0
            conditions_array[i].external = 0
            conditions_array[i].aux = 0
            conditions_array[i].pulseWidthQualifier = 0

            for channel_name in channel_names:
                setattr(conditions_array[i], f"channel{channel_name}", 1)

        status = self.ps.ps6000SetTriggerChannelConditions(
            self.handle,
            ctypes.byref(conditions_array),
            len(condition_channel_lists)
        )
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger conditions: {e}")

    def set_trigger_directions(self, channels: List[str]) -> None:
        """Set falling-edge direction for participating channels, NONE elsewhere."""
        # PS6000_THRESHOLD_DIRECTION literals: NONE = 2 (alias of RISING),
        # FALLING = 3. These are the PS6000's own values - do not share with
        # the PS3000a enum, whose NONE differs.
        none_dir = 2
        falling = 3

        directions = {name: (falling if name in channels else none_dir)
                      for name in ('A', 'B', 'C', 'D')}

        status = self.ps.ps6000SetTriggerChannelDirections(
            self.handle,
            directions['A'],
            directions['B'],
            directions['C'],
            directions['D'],
            2,  # external: RISING - required even if not used
            2   # aux: NONE
        )
        try:
            assert_pico_ok(status)
        except Exception as e:
            raise RuntimeError(f"Failed to set trigger directions: {e}")

    def get_no_of_captures(self) -> int:
        """
        Number of completed rapid-block captures. Valid after run_block
        finished, or after stop() interrupted it (partial batch).
        """
        n = ctypes.c_uint32(0)
        status = self.ps.ps6000GetNoOfCaptures(self.handle, ctypes.byref(n))
        assert_pico_ok(status)
        return n.value

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
