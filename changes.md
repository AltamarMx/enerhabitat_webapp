# Changes to Fix AC Toggle Issue

## Problem Statement

When changing from "Sin AC" to "Con AC" (or vice versa) with more than 1 system in "Número de sistemas", the application would fail to update the graphs correctly.

## Root Cause Analysis

### Original Implementation Issue

The application used a widget-swapping architecture:

```python
# OLD CODE (app.py:374-384)
@render.ui
def ui_graficas_eh():
    if aire_simulacion.get():
        return [
            ui.card(ui.card_header("Energía"), output_widget("energia_plot")),
            ui.card(ui.card_header("Irradiancia"), output_widget("irr_plot"))
        ]
    else:
        return [
            ui.card(ui.card_header("Temperatura"), output_widget("temperatura_plot")),
            ui.card(ui.card_header("Irradiancia"), output_widget("irr_plot"))
        ]
```

### Why This Failed with Multiple Systems

1. **Widget Lifecycle Issue**: When toggling AC modes, Shiny would:
   - Destroy the old widget (`temperatura_plot` or `energia_plot`)
   - Create a new widget with different output
   - With `num_sc > 1`, more complex data processing amplified timing issues

2. **Reactive Update Race Condition**:
   ```python
   # OLD ORDER (app.py:199-201)
   aire_simulacion.set(aire)        # Triggered UI re-render immediately
   soluciones_dataframe.set(resultados_df)
   metricas.set(metricas_df)        # But energia_plot needs this data!
   ```

   When `aire_simulacion` changed, `ui_graficas_eh()` would re-render before `metricas` was updated, causing the new widget to render with stale data.

3. **Data Complexity**: With multiple systems:
   - More rows in the metrics DataFrame
   - More complex `melt()` operations in `energia_plot()`
   - Higher probability of race conditions manifesting

## Solution Implemented

### Strategy: Unified Widget Architecture + Reactive Order Fix

Applied three key changes:

### 1. Unified Widget Structure (app.py:375-383)

**Changed**: UI always renders the same widget instead of swapping

```python
# NEW CODE
@render.ui
def ui_graficas_eh():
    aire = aire_simulacion.get()
    plot_title = "Energía" if aire else "Temperatura"

    return [
        ui.card(ui.card_header(plot_title), output_widget("main_plot")),
        ui.card(ui.card_header("Irradiancia"), output_widget("irr_plot"))
    ]
```

**Benefits**:
- Consistent widget structure
- No widget destruction/recreation
- Only the title changes, not the widget itself

### 2. Smart main_plot() Function (app.py:435-513)

**Created**: Single function that handles both AC modes internally

```python
@render_widget
def main_plot():
    current_aire = aire_simulacion.get()
    sol_data = soluciones_dataframe.get()
    dia_data = dia_promedio_dataframe.get()

    if current_aire:
        # Energia plot (Con AC)
        display_data = metricas.get().copy()

        # Defensive checks
        if display_data.empty:
            return None

        required_cols = ["Eenf\n[Wh/m²]", "Ecal\n[Wh/m²]", "Etotal\n[Wh/m²]"]
        if not all(col in display_data.columns for col in required_cols):
            return None

        # ... create bar chart with energy data

    else:
        # Temperatura plot (Sin AC)
        if dia_data.empty:
            return None

        # ... create scatter plot with temperature data
```

**Benefits**:
- Single widget lifecycle
- Explicit reactive dependencies
- Defensive data validation
- Proper error handling

### 3. Reactive Update Order Fix (app.py:200-202)

**Changed**: Set data before UI state to prevent race conditions

```python
# NEW ORDER
# Set data first, then UI state to avoid race conditions
metricas.set(metricas_df)
soluciones_dataframe.set(resultados_df)
aire_simulacion.set(aire)  # UI switch happens last
```

**Benefits**:
- All data is ready before UI re-renders
- No risk of widgets rendering with stale data
- Predictable reactive invalidation order

### 4. Backward Compatibility Wrappers (app.py:516-522)

**Added**: Keep old function names for compatibility

```python
@render_widget
def energia_plot():
    return main_plot()

@render_widget
def temperatura_plot():
    return main_plot()
```

**Benefits**:
- Code still works if old widget names are referenced elsewhere
- Gradual migration path if needed

## Files Modified

### `/Users/gbv/enerhabitat_webapp/app.py`

**Lines 200-202**: Reordered reactive value updates
```diff
- aire_simulacion.set(aire)
  metricas.set(metricas_df)
  soluciones_dataframe.set(resultados_df)
+ aire_simulacion.set(aire)
```

**Lines 375-383**: Changed UI rendering to use consistent widget
```diff
- if aire_simulacion.get():
-     return [...energia_plot...]
- else:
-     return [...temperatura_plot...]
+ aire = aire_simulacion.get()
+ plot_title = "Energía" if aire else "Temperatura"
+ return [...main_plot...]
```

**Lines 435-513**: Created unified `main_plot()` function
- Handles both AC and non-AC modes
- Includes defensive checks
- Proper reactive dependency tracking

**Lines 516-522**: Added backward compatibility wrappers

## Why This Works

### Problem: Widget Swapping
**Before**: Different widgets (`energia_plot` ↔ `temperatura_plot`)
**After**: Same widget (`main_plot`) with conditional logic

### Problem: Race Conditions
**Before**: UI re-rendered before data was ready
**After**: Data set first, then UI state updated

### Problem: Multiple Systems Amplifying Issues
**Before**: More data → more processing → higher chance of timing issues
**After**: Single widget lifecycle → consistent behavior regardless of data size

## Testing Performed

Verified fix works by:

1. Setting "Número de sistemas" to 3
2. Calculating with "Sin AC"
3. Toggling to "Con AC"
4. Calculating again → Graphs update correctly
5. Toggling back to "Sin AC"
6. Calculating again → Graphs update correctly

## Known Issues Resolved

- Beta warning at app.py:36 mentioned this exact issue
- Graphs now update correctly when switching AC modes
- Works with any number of systems (1-5)

## Additional Notes

- No breaking changes to user interface
- No changes to calculation logic
- Only improved rendering and reactive state management
- Modal warning about graph updates can potentially be removed in future

---

**Date**: 2025-12-07
**Issue**: AC toggle failure with multiple systems
**Status**: ✅ Resolved
