"""
MCS (Material Control System) Log Parser.

Parses AMHS/MCS log format with bracketed key-value pairs.

Supported formats:
  1. Original format (two-parameter):
     2025-12-05 00:00:35.404 [REMOVE=CommandID, CarrierID] [Key=Value], [Key2=Value2], ...
     2025-12-05 00:00:36.322 [UPDATE=336182, BBADFB0397] [CurrentLocation=B1ACNV13301-120]
  
  2. Simplified format (single-parameter):
     2025-12-09 00:00:01.443 [UPDATE=CarrierID] [CarrierLoc=B1ACNV13301-108]
     2025-12-09 00:00:13.493 [ADD=SDADTN490140] [CarrierID=SDADTN490140], [CarrierLoc=B1ACNV13301-129]

Log structure:
  - Timestamp: YYYY-MM-DD HH:MM:SS.mmm
  - Action header: [ACTION=CommandID, CarrierID] or [ACTION=CarrierID]
    where ACTION is ADD, UPDATE, or REMOVE
  - Key-value pairs: [Key=Value] format, comma-separated

Signal name mapping:
  - CarrierLoc, CarrierLocation → CurrentLocation (for carrier tracking compatibility)

Each key-value pair is treated as a signal update for the carrier (device_id).
"""

import re
import sys
from datetime import datetime
from typing import Optional, List, Tuple
from .base_parser import GenericTemplateLogParser, _infer_type_fast, _parse_value_fast, _fast_ts
from plc_visualizer.models import LogEntry, ParseResult, ParsedLog, ParseError, SignalType


class MCSLogParser(GenericTemplateLogParser):
    """Parser for MCS (Material Control System) / AMHS log format.
    
    This parser handles logs with the following format:
    - Each line starts with a timestamp
    - Followed by an action header: [ACTION=CommandID, CarrierID]
    - Followed by key-value pairs: [Key=Value], [Key2=Value2], ...
    
    The CarrierID is used as the device_id, and each key-value pair
    becomes a separate LogEntry (signal).
    """
    
    name = "mcs_log"
    
    # Regex for initial line detection
    # Matches both formats:
    #   [ACTION=CommandID, CarrierID] [Key=Value]  (original format)
    #   [ACTION=CarrierID] [Key=Value]              (simplified format)
    LINE_RE = re.compile(
        r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s+'  # timestamp
        r'\[(?P<action>ADD|UPDATE|REMOVE)=(?P<first_id>[^,\]]+)(?:,\s*(?P<second_id>[^\]]+))?\]'  # action header
        r'\s*(?P<kvpairs>.*)?$'  # remaining key-value pairs
    )
    
    # Regex to extract individual [Key=Value] pairs
    KV_PAIR_RE = re.compile(r'\[([^=\]]+)=([^\]]*)\]')
    
    # Override device ID regex - CarrierID format (alphanumeric)
    DEVICE_ID_REGEX = re.compile(r'([A-Za-z0-9_-]+)$')
    
    # Type mapping with additional MCS-specific types
    TYPE_MAP = {
        "boolean": SignalType.BOOLEAN,
        "bool": SignalType.BOOLEAN,
        "string": SignalType.STRING,
        "str": SignalType.STRING,
        "integer": SignalType.INTEGER,
        "int": SignalType.INTEGER,
        "true": SignalType.BOOLEAN,
        "false": SignalType.BOOLEAN,
    }
    
    # Known boolean keys for type inference
    BOOLEAN_KEYS = {
        'IsBoost', 'IsMultiJob', 'IsMultipleDestination', 
        'IsLocationGroupOrder', 'IsExecuteCommand'
    }
    
    # Known integer keys
    INTEGER_KEYS = {
        'Priority', 'AltCount', 'AltCount2', 'WaitCount', 'CirculationCount'
    }
    
    # Known state/enum keys - these are strings representing states
    STATE_KEYS = {
        'TransferState', 'TransferState2', 'TransferAbnormalState', 
        'TransferAbnormalState2', 'ResultCode', 'ResultCode2', 'CommandType'
    }
    
    # Signal name mapping - normalize alternative names to canonical forms
    # This allows carrier tracking to work with different log format variations
    SIGNAL_NAME_MAP = {
        'CarrierLoc': 'CurrentLocation',  # Map CarrierLoc to CurrentLocation for carrier tracking
        'CarrierLocation': 'CurrentLocation',
    }

    def parse(
        self,
        file_path: str,
        num_workers: Optional[int] = None,
        *,
        use_processes: bool = False,
    ) -> ParseResult:
        """Override to force single-threaded parsing.
        
        MCS parser uses _parse_line_to_entries which returns multiple entries
        per line, incompatible with the generic multiprocessing workers.
        """
        # Always use single-threaded parsing for MCS format
        return self._parse_single(file_path)
    
    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the file."""
        try:
            with open(file_path, 'r', encoding='utf-8-sig', buffering=self.BUFFER_SIZE) as f:
                checked = matched = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    checked += 1
                    
                    # Check for MCS format markers
                    if self.LINE_RE.match(line):
                        matched += 1
                    
                    if checked >= 10:
                        break
                
                # Need at least 60% match rate
                return checked > 0 and (matched / checked) >= 0.6
        except Exception:
            return False

    def _infer_type_for_key(self, key: str, value: str) -> SignalType:
        """Infer signal type based on key name and value."""
        # Check known boolean keys
        if key in self.BOOLEAN_KEYS:
            return SignalType.BOOLEAN
        
        # Check known integer keys  
        if key in self.INTEGER_KEYS:
            return SignalType.INTEGER
            
        # Check known state keys (always string)
        if key in self.STATE_KEYS:
            return SignalType.STRING
        
        # Value-based inference
        upper_val = value.upper()
        if upper_val in ('TRUE', 'FALSE'):
            return SignalType.BOOLEAN
        
        # Try integer
        try:
            int(value)
            return SignalType.INTEGER
        except ValueError:
            pass
        
        return SignalType.STRING
    
    def _parse_value_for_type(self, value: str, signal_type: SignalType):
        """Parse value based on signal type."""
        if signal_type == SignalType.BOOLEAN:
            upper_val = value.upper()
            return upper_val in ('TRUE', '1', 'YES', 'ON')
        
        if signal_type == SignalType.INTEGER:
            try:
                return int(value)
            except ValueError:
                return value  # Fallback to string
        
        return value

    def _parse_line_to_entries(self, line: str) -> List[Tuple[str, str, datetime, any, SignalType]]:
        """Parse a single line into multiple (device_id, signal_name, timestamp, value, type) tuples.
        
        Returns a list because each line may contain multiple key-value pairs,
        each becoming a separate signal entry.
        """
        entries = []
        
        # Match the line format
        m = self.LINE_RE.match(line)
        if not m:
            return entries
        
        # Extract components
        ts_str = m.group('ts')
        action = m.group('action')
        first_id = m.group('first_id').strip()
        second_id_match = m.group('second_id')
        kvpairs_str = m.group('kvpairs') or ''
        
        # Determine command_id and carrier_id based on format
        if second_id_match:
            # Original format: [ACTION=CommandID, CarrierID]
            command_id = first_id
            carrier_id = second_id_match.strip()
        else:
            # Simplified format: [ACTION=CarrierID]
            command_id = ''  # No command ID in this format
            carrier_id = first_id
        
        # Parse timestamp
        try:
            timestamp = _fast_ts(ts_str)
        except Exception:
            try:
                timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                return entries  # Can't parse timestamp
        
        # Use carrier_id as device_id
        device_id = sys.intern(carrier_id)
        
        # Add an entry for the action itself
        action_signal = sys.intern(f"_Action")
        entries.append((
            device_id,
            action_signal, 
            timestamp,
            action,
            SignalType.STRING
        ))
        
        # Add CommandID as a signal (only if present)
        if command_id:
            entries.append((
                device_id,
                sys.intern("_CommandID"),
                timestamp,
                command_id,
                SignalType.STRING
            ))
        
        # Parse all [Key=Value] pairs
        for key, value in self.KV_PAIR_RE.findall(kvpairs_str):
            key = key.strip()
            value = value.strip()
            
            if not key:
                continue
            
            # Apply signal name mapping to normalize alternative names
            key = self.SIGNAL_NAME_MAP.get(key, key)
            
            # Skip empty values or "None" for cleaner visualization
            if value == '' or value == 'None':
                continue
            
            # Infer type
            signal_type = self._infer_type_for_key(key, value)
            
            # Parse value
            parsed_value = self._parse_value_for_type(value, signal_type)
            
            entries.append((
                device_id,
                sys.intern(key),
                timestamp,
                parsed_value,
                signal_type
            ))
        
        return entries

    def _fast_parse_line(self, line: str, did_re: re.Pattern) -> Optional[LogEntry]:
        """Fast parse is not suitable for multi-entry lines.
        
        For MCS format, we need to return multiple entries per line,
        so we override _parse_single instead.
        """
        return None  # Use the overridden _parse_single method

    def _parse_single(self, file_path: str) -> ParseResult:
        """Parse the file, handling multiple entries per line."""
        import time
        start_time = time.perf_counter()
        
        entries: List[LogEntry] = []
        signals: set = set()
        devices: set = set()
        errors: List[ParseError] = []
        
        out_of_order = False
        last_ts: Optional[datetime] = None
        
        try:
            with open(file_path, 'r', encoding='utf-8-sig', buffering=self.BUFFER_SIZE) as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse line into multiple entries
                        line_entries = self._parse_line_to_entries(line)
                        
                        if not line_entries:
                            # Line didn't match expected format
                            continue
                        
                        for device_id, signal_name, timestamp, value, signal_type in line_entries:
                            # Chrono check
                            if self.USE_CHRONO_DETECTION:
                                if last_ts and timestamp < last_ts:
                                    out_of_order = True
                                last_ts = timestamp
                            
                            entry = LogEntry(
                                device_id=device_id,
                                signal_name=signal_name,
                                timestamp=timestamp,
                                value=value,
                                signal_type=signal_type,
                            )
                            entries.append(entry)
                            
                            signals.add(f"{device_id}::{signal_name}")
                            devices.add(device_id)
                    
                    except Exception as e:
                        errors.append(
                            ParseError(line_num, line[:100], str(e))
                        )
        
        except FileNotFoundError:
            errors.append(ParseError(0, "", f"File not found: {file_path}"))
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)
        except Exception as e:
            errors.append(ParseError(0, "", f"Failed to read file: {e}"))
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)
        
        if not entries:
            elapsed = time.perf_counter() - start_time
            return ParseResult(data=None, errors=errors, processing_time=elapsed)
        
        # Sort if needed
        if not self.USE_CHRONO_DETECTION or out_of_order:
            entries.sort(key=lambda e: e.timestamp)
        
        parsed = ParsedLog(entries=entries, signals=signals, devices=devices)
        elapsed = time.perf_counter() - start_time
        return ParseResult(data=parsed, errors=errors, processing_time=elapsed)

    def parse_time_window(
        self,
        file_path: str,
        start_time: datetime,
        end_time: datetime
    ) -> ParseResult:
        """Optimized time-window parsing for MCS format."""
        import time
        parse_start = time.perf_counter()
        
        entries = []
        errors = []
        devices = set()
        signals = set()
        
        seen_start = False
        consecutive_out_of_range = 0
        max_consecutive = 1000
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        line_entries = self._parse_line_to_entries(line)
                        
                        if not line_entries:
                            continue
                        
                        # Use first entry's timestamp for window check
                        first_ts = line_entries[0][2]
                        
                        if first_ts < start_time:
                            consecutive_out_of_range = 0
                            continue
                        elif first_ts >= end_time:
                            consecutive_out_of_range += 1
                            if seen_start and consecutive_out_of_range > max_consecutive:
                                break
                            continue
                        else:
                            seen_start = True
                            consecutive_out_of_range = 0
                            
                            for device_id, signal_name, timestamp, value, signal_type in line_entries:
                                entry = LogEntry(
                                    device_id=device_id,
                                    signal_name=signal_name,
                                    timestamp=timestamp,
                                    value=value,
                                    signal_type=signal_type,
                                )
                                entries.append(entry)
                                devices.add(device_id)
                                signals.add(f"{device_id}::{signal_name}")
                    
                    except Exception as e:
                        errors.append(ParseError(
                            line=line_num,
                            content=line[:100],
                            reason=str(e)
                        ))
        
        except Exception as e:
            errors.append(ParseError(
                line=0,
                content="",
                reason=f"File read error: {e}"
            ))
            return ParseResult(data=None, errors=errors)
        
        elapsed = time.perf_counter() - parse_start
        
        parsed_log = ParsedLog(
            entries=entries,
            signals=signals,
            devices=devices,
            time_range=(start_time, end_time)
        )
        return ParseResult(data=parsed_log, errors=errors, processing_time=elapsed)


# Register the parser
from .parser_registry import parser_registry
parser_registry.register(MCSLogParser())
