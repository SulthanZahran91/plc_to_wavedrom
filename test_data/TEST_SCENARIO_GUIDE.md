# Comprehensive Test Scenario - Package Sorting Line

This test scenario demonstrates all major features of the PLC Visualizer across 3 primary windows: **Map Viewer**, **Timing Diagram**, and **Signal Interval Analysis**.

## Scenario Overview

**System**: Automated package sorting line with priority routing
**Duration**: 60 seconds (10:00:00 - 10:01:00)
**Key Features**: Racing conditions, changing trends, system stress testing, error recovery

### System Layout

```
                                    ┌─────────────┐
                                    │  Priority   │
                     ┌──[DIV-1]────▶│  Exit (P2)  │
                     │              └─────────────┘
[Infeed]──▶[Merge]──▶│
                     │              ┌─────────────┐
                     └──[DIV-2]────▶│  Normal (P1)│
                            │       └─────────────┘
                            │       ┌─────────────┐
                            └──────▶│  Reject (P3)│
                                    └─────────────┘
```

**Components**:
- 10 Conveyor Belts (CNV13301-13310)
- 3 Diverters (DV14001-14003)
- 3 Exit Ports (PT15001-15003)

## Timeline & Events

### Phase 1: Startup (0-5s)
- System initialization
- All conveyors transition from Idle → Running
- Speed ramps up to 0.5 m/s
- First sensor calibration (A signals initialize to 0)

**What to observe**:
- Map Viewer: Gradual color changes from gray (idle) to green (running)
- Timing Diagram: Clean status transitions
- Interval Window: Initial baseline timing

### Phase 2: Light Load (5-20s)
- First packages arrive at ~1-2 second intervals
- Smooth processing through the system
- Package detection patterns: A=0 → A=1 → A=0 (single package)
- Diverter routing decisions begin

**What to observe**:
- Map Viewer: Packages flow smoothly, sensors light up yellow (A=1)
- Timing Diagram: Regular pulse patterns on A signals, uniform spacing
- Interval Window:
  - Change-to-change: ~4-5 second intervals
  - True pulse width: ~3-4 seconds (transit time)

### Phase 3: **RACING CONDITIONS BEGIN** (20-35s)
- Package arrival rate increases dramatically
- Intervals drop to 100-250ms between packages
- Multiple packages in system simultaneously
- Competing sensor triggers: A=1→A=2→A=3 (congestion)
- B signal (package counter) rapidly incrementing
- Speed increases to 0.7-0.9 m/s to handle load

**What to observe** ⭐:
- Map Viewer:
  - Multiple belts active simultaneously
  - Color changes: Yellow→Green→Blue (A=1→A=2→A=3)
  - B signal causes orange/red colors (counter values 15-55)
- Timing Diagram:
  - **Overlapping waveforms** - multiple A signals high at same time
  - Rapid transitions creating dense patterns
  - Speed signal ramping up
- Interval Window ⭐⭐⭐:
  - **Change-to-change intervals DROP dramatically** from ~4s to ~0.08-0.15s
  - **Time-window binning** shows clear trend: early bins sparse, later bins dense
  - **Percentile view** shows distribution shift
  - Pattern matching can find "A=1→A=2→A=3" sequences (congestion pattern)

### Phase 4: **PEAK STRESS** (35-43s)
- Maximum throughput reached
- System cannot keep up
- Racing intensifies: packages as close as 20-80ms apart
- Speed maxes out at 1.0 m/s
- B counters climb to 50-68 (high load indicator)
- **SYSTEM OVERLOAD** at 42.5s:
  - Main infeed belts STOP
  - Belt 1 enters ERROR state at T+44s
  - Downstream belts continue processing backlog

**What to observe** ⭐⭐:
- Map Viewer:
  - Red indicators for high B values (>50)
  - Status transitions: Running → Stopped (yellow with pause symbol)
  - Belt 1: Error state (light red background with red X overlay)
  - Downstream still processing (blue/green colors)
- Timing Diagram:
  - **Sudden drop** in Speed signals to 0
  - Status signals show clear ERROR state on CNV13301
  - Continued activity on downstream (CNV13305-13309)
- Interval Window:
  - **Shortest intervals recorded** (~20-40ms)
  - **Bimodal distribution** if analyzing entire period
  - True pulse width shows **minimal spacing** between packages

### Phase 5: Recovery (44-48s)
- Error cleared at T+46s (Idle)
- System restart at T+47s
- Gradual speed ramp back to 0.5 m/s
- Downstream belts continue at elevated speed (0.8-0.9 m/s)

**What to observe**:
- Map Viewer: Error clears, green returns to upstream
- Timing Diagram: Status recovery sequence visible
- Interval Window: Processing backlog shows sustained activity

### Phase 6: Stabilization (48-60s)
- Return to normal operations
- Package spacing returns to ~500ms intervals
- Speeds stabilize at 0.5-0.6 m/s
- Continued steady processing to end

**What to observe**:
- Map Viewer: Steady state operation, consistent colors
- Timing Diagram: Regular patterns resume
- Interval Window: Intervals increase back to 4-5 second range

## Testing Each Window

### 1. Map Viewer Window (📖 Map Viewer)

**Load Files**:
1. Map: `test_data/sorting_line_map.xml`
2. Signals: `test_data/sorting_line_signals.csv`
3. Rules (optional): `test_data/sorting_line_rules.yaml`

The YAML rules file defines color mappings for all signals:
- Status-based colors (Running=Green, Error=Red X, Stopped=Yellow pause)
- A signal colors (0=Gray, 1=Yellow, 2=Green, 3=Blue for congestion levels)
- B counter colors (gradient from amber to dark red for values 1-60+)
- Speed colors (light blue to dark blue for 0-1.0 m/s)
- LoadCount colors (green shades for throughput)

**What to Test**:

✅ **Real-time Playback**:
- Use media controls to play through timeline
- Observe color changes reflecting signal states
- Watch flow from infeed through diverters to exits

✅ **Status Visualization**:
- Green = Running conveyors
- Gray = Idle/Stopped with pause symbol ‖
- Red X overlay = Error state (Belt 1 at 44s)

✅ **Signal-based Colors**:
- Yellow/Green/Blue = A signal states (package detection)
- Orange/Red = High B values (counter >20, >50, >80)
- Blue shades = Speed levels

✅ **Date/Time Navigation**:
- Jump to specific events:
  - `10:00:27` - First racing condition
  - `10:00:39` - Peak racing (80ms intervals)
  - `10:00:44` - Error state
  - `10:00:47` - Recovery

✅ **Multiple Device Coordination**:
- Watch packages flow through: Belt1→Belt2→Belt3→Belt4→Diverter1
- Observe diverter routing: Priority path (upper) vs Normal path (lower)
- Exit counts increment at ports

### 2. Timing Diagram Window (⚙ Timing Diagram)

**Load**: `test_data/sorting_line_signals.csv`

**What to Test**:

✅ **Waveform Patterns**:
- Status signals: Clean digital transitions
- A signals: Pulse trains showing package detection
- Speed signals: Analog-style ramping
- B signals: Step increases (counter behavior)

✅ **Racing Condition Visualization** ⭐:
- Time range: 10:00:27 - 10:00:42
- Observe: **Multiple A signals active simultaneously**
- Look for: Overlapping highs indicating congestion
- Compare: CNV13301, CNV13302, CNV13303 A signals all high together

✅ **System Event Correlation**:
- Zoom to 10:00:42.5 - 10:00:43.5
- See: Speed signals dropping to 0
- See: Status signals changing to Stopped/Error
- Correlation: Upstream stops, downstream continues

✅ **Signal Filtering**:
- Filter to just "Speed" signals → see load response
- Filter to just "Status" signals → see state machine
- Filter to "A" signals → see package flow patterns

✅ **Zoom & Pan**:
- Zoom into racing period (33-42s) to see millisecond-level detail
- Pan through timeline to follow package through system
- Use time range selector for precise analysis

✅ **Viewport Synchronization**:
- Open both Timing Diagram and Map Viewer
- Seek in one window, observe the other updates
- Demonstrates synchronized playback across views

### 3. Signal Interval Window (📈 Transition Intervals)

**Load**: `test_data/sorting_line_signals.csv`

**Best Signals to Analyze**:

#### Test Case A: `B1ACNV13301-104@D19` Signal `A` ⭐⭐⭐

This is the **best demonstration** of racing conditions and changing trends!

**Setup**:
- Select: Device=B1ACNV13301-104@D19, Signal=A
- Measurement: Change-to-change intervals
- Time-window: Try 5-second bins

**What to Observe**:

✅ **Dramatic Trend Change**:
- Early intervals (0-20s): ~4-5 seconds between changes
- Racing period (27-42s): ~0.08-0.4 seconds (100-400ms!)
- **~30-50x speedup** clearly visible in histogram

✅ **Time-Window Binning**:
- Early bins (0-5s, 5-10s): Sparse, few intervals, all long
- Middle bins (25-30s, 30-35s): Dense, many intervals, getting shorter
- Late bins (35-40s, 40-45s): Extremely dense, shortest intervals
- Recovery bins (50-55s, 55-60s): Return to normal

✅ **Percentile Analysis**:
- P10: Shows minimum typical interval (~80ms during racing)
- P50 (Median): Clear bimodal behavior (~4s normal, ~200ms racing)
- P90: Shows maximum intervals (~5s)

✅ **Pattern Matching**:
- Custom pattern: `0 -> 1 -> 0` (single package)
  - Common in early period
- Custom pattern: `0 -> 1 -> 2` (congestion starting)
  - Appears at 27s, 33s, 39s
- Custom pattern: `1 -> 2 -> 3` (heavy congestion)
  - Only during peak stress (39-41s)

#### Test Case B: `B1ACNV13304-104@D19` Signal `B`

**Setup**:
- Select: Device=B1ACNV13304-104@D19, Signal=B
- Measurement: Change-to-change intervals

**What to Observe**:

✅ **Incremental Counter Pattern**:
- Values: 15, 22, 28, 35, 42, 48, 55, 58, 62, 68
- Intervals between increments show **package processing rate**
- Racing period: Rapid increments (seconds apart)
- Normal period: Slow increments (5-10 seconds apart)

#### Test Case C: `B1ACNV13301-104@D19` Signal `Status`

**Setup**:
- Select: Device=B1ACNV13301-104@D19, Signal=Status
- Measurement: True pulse width
- Pattern: Running state duration

**What to Observe**:

✅ **Operating Periods**:
- First run: 1.5s → 42.5s = ~41 seconds
- Stop duration: 42.5s → 47s = 4.5 seconds
- Second run: 47s → 60s = 13+ seconds

✅ **Custom Token Pattern**:
- Pattern: `Idle -> Running -> Stopped -> Error -> Idle -> Running`
- Should match the error recovery sequence
- Demonstrates state machine behavior

#### Test Case D: `B1ACPT15002-104@D19` Signal `LoadCount`

**Setup**:
- Select: Device=B1ACPT15002-104@D19 (Priority Exit Port)
- Signal: LoadCount
- Measurement: Change-to-change intervals

**What to Observe**:

✅ **Throughput Analysis**:
- Increments: 1→2→3→4→5→6
- Interval between counts = package delivery rate to priority exit
- Shows effectiveness of priority routing
- Compare with PT15001 (normal exit) for routing distribution

### Advanced Testing: Multi-Window Analysis

**Scenario**: Track a single package through the entire system

1. **Map Viewer**: Set to 10:00:27.000
2. **Timing Diagram**: Zoom to 10:00:27 - 10:00:32
3. **Interval Window**: Analyze CNV13301 Signal A

**Follow the Package**:
- T+27.100: Detected on Belt1 (CNV13301 A=1)
- T+27.450: Reaches Belt2 (CNV13302 A=1)
- T+27.850: Reaches Belt3 (CNV13303 A=1)
- T+28.250: Reaches Belt4 (CNV13304 A=1)
- T+29.050: Diverter decision (DV14001 A=2 = Priority)
- T+29.850: Priority path (CNV13307 A=1)
- T+30.850: Express belt (CNV13309 A=1)
- T+31.650: Arrives at priority port (PT15002 A=1, LoadCount=3)

**Transit time**: ~4.5 seconds from infeed to exit

## Key Performance Indicators Demonstrated

### Racing Conditions ✅
- **Achieved**: Inter-arrival times as low as 20ms
- **Location**: T+39-42s on CNV13301, CNV13302, CNV13303
- **Evidence**: Overlapping sensor activations, A signal values reaching 3

### Changing Trends ✅
- **Metric**: Package arrival intervals
- **Change**: ~5000ms → ~80ms (62x reduction)
- **Visualization**: Time-window binning in interval window shows clear shift

### System Stress ✅
- **Trigger**: Throughput exceeds capacity at T+42.5s
- **Response**: Automatic stop, error state, recovery
- **Duration**: 4.5 second pause for error handling

### Multi-Path Routing ✅
- **Priority Path**: ~50% of packages (DV14001 A=1 or A=3)
- **Normal Path**: ~40% of packages (DV14001 A=2)
- **Reject Path**: Available via DV14002, DV14003 (simulated QC)

## Expected Insights

After loading and exploring this scenario, you should be able to:

1. **Map Viewer**: Visualize real-time system state and package flow
2. **Timing Diagram**: Identify temporal relationships and correlations between signals
3. **Interval Window**: Quantify timing patterns, detect anomalies, prove system behavior

### Specific Conclusions from Data:

- ✅ System handles **normal load** (1 package/5s) reliably
- ✅ System shows **racing conditions** when load increases to 10-15 packages/s
- ✅ **Congestion detection** works: A signal reaches values 2-3 when multiple packages present
- ✅ **Error recovery** is automatic: 2s idle, then restart at reduced speed
- ✅ **Priority routing** functions: high-value packages take faster path
- ✅ **Throughput measurements** possible: LoadCount intervals = delivery rate

## Files Reference

- **Map**: `test_data/sorting_line_map.xml` (1080x600 canvas, 19 objects)
- **Signals**: `test_data/sorting_line_signals.csv` (327 data points, 60s duration)
- **Rules**: `test_data/sorting_line_rules.yaml` (color mapping configuration)
- **This Guide**: `test_data/TEST_SCENARIO_GUIDE.md`

## Quick Start

1. Launch PLC Visualizer
2. Load `sorting_line_signals.csv` via main window
3. Click "📖 Map Viewer"
   - Open Map → Select `sorting_line_map.xml`
   - Load the `sorting_line_rules.yaml` if your map viewer supports it
4. Click "⚙ Timing Diagram" → Explore timeline
5. Click "📈 Transition Intervals" → Analyze CNV13301 Signal A
6. Follow the testing steps above!

---

**Generated**: 2025-10-27
**Scenario Duration**: 60 seconds
**Complexity**: High (racing conditions, multi-path routing, error handling)
**Recommended For**: Feature demonstration, performance testing, training
