#### GUI IMPORTS
from ccpn.ui.gui.widgets.PipelineWidgets import GuiPipe, _getWidgetByAtt
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.GLLinearRegionsPlot import GLTargetButtonSpinBoxes

#### NON GUI IMPORTS
from ccpn.framework.lib.pipeline.PipeBase import SpectraPipe, PIPE_USER
from ccpn.util.Logging import getLogger
import numpy as np
import pandas as pd

########################################################################################################################
###   Attributes:
########################################################################################################################

PipeName = 'Water Suppression QC'

# Attribute names for GUI widgets
WaterRegion = 'Water_Region'
DefaultWaterRegion = (4.7, 4.8)  # Default D2O water region

########################################################################################################################
##########################################      ALGORITHM       ########################################################
########################################################################################################################

# Check water suppression effectiveness for D2O
# Water region: User-selectable via popup (default 4.7-4.8 ppm)
#
# Method: Baseline shape detection
# Compares the baseline at the EDGES of the water region to the MIDDLE
# A broad water hump will have elevated middle compared to edges
#
# Water_check = PASS if baseline is relatively flat (good suppression)
# Water_check = CHECK if middle is elevated compared to edges (broad hump)

# Adjustable settings
BASELINE_ELEVATION_THRESHOLD = 0.8  # If middle baseline is 0.8x higher than edges, fails
EDGE_PERCENTAGE = 0.15  # Use outer 15% on each side as "edges"

########################################################################################################################
##########################################     GUI PIPE    #############################################################
########################################################################################################################


class WaterGuiPipe(GuiPipe):
    preferredPipe = True
    pipeName = PipeName

    def __init__(self, name=pipeName, parent=None, project=None, **kwds):
        super(WaterGuiPipe, self).__init__(parent=parent, name=name, project=project, **kwds)
        self._parent = parent

        row = 0
        # Water region selector
        self.regionLabel = Label(self.pipeFrame, text=WaterRegion, grid=(row, 0))
        setattr(self, WaterRegion, GLTargetButtonSpinBoxes(self.pipeFrame, application=self.application,
                                                           values=DefaultWaterRegion, orientation='v',
                                                           decimals=4,
                                                           step=0.001,
                                                           grid=(row, 1)))
        row += 1

        self._updateWidgets()

    def _updateWidgets(self):
        pass


########################################################################################################################
##########################################       PIPE      #############################################################
########################################################################################################################


class WaterPipe(SpectraPipe):
    guiPipe = WaterGuiPipe
    pipeName = PipeName
    pipeCategory = PIPE_USER

    _kwargs = {
        WaterRegion: DefaultWaterRegion
    }

    def runPipe(self, spectra, **kwargs):
        """
        Check water suppression for D2O samples.
        User can select the water region via popup window.
        
        Baseline shape detection:
        - Divides water region into edges (outer portions) and middle
        - Calculates baseline using lower percentile (to ignore peaks)
        - Compares middle baseline to edge baseline
        - A broad water hump will have elevated middle
        
        Water_check = PASS if baseline is flat (good suppression)
        Water_check = CHECK if middle is elevated (broad hump = poor suppression)
        
        Adjustable settings at top of file:
        - BASELINE_ELEVATION_THRESHOLD: Max allowed ratio of middle to edges (default 0.8)
        - EDGE_PERCENTAGE: How much of each side to use as edges (default 0.15 = 15%)
        """
        # Get water region from GUI
        waterRegion = self._kwargs[WaterRegion]
        
        # Pipe columns
        pipeColumns = ['Water_edge_baseline', 'Water_middle_baseline', 'Water_elevation_ratio', 'Water_check']

        # Establish dataTable
        qcDataTable = self.project.getByPid('DT:QC_Results')
        if not qcDataTable:
            columns = ['Spectrum'] + pipeColumns
            qcDataTable = self.project.newDataTable(name='QC_Results', data=pd.DataFrame(columns=columns))
        else:
            # Only add columns if they don't already exist
            for col in pipeColumns:
                if col not in qcDataTable.data.columns:
                    qcDataTable.data[col] = None

        for spectrum in spectra:
            spectrumName = spectrum.name
            x = spectrum.positions
            y = spectrum.intensities

            # Normalize intensities
            y_norm = y / np.max(y)

            # Extract water region (user-selected)
            region_min = min(waterRegion[0], waterRegion[1])
            region_max = max(waterRegion[0], waterRegion[1])
            
            water_mask = (x >= region_min) & (x <= region_max)
            water_x = x[water_mask]
            water_y = y_norm[water_mask]

            # Initialize results
            edge_baseline = float('nan')
            middle_baseline = float('nan')
            elevation_ratio = float('nan')
            water_check = 'PASS'

            if len(water_y) > 0:
                # Calculate region boundaries
                total_points = len(water_y)
                edge_points = int(total_points * EDGE_PERCENTAGE)
                
                if edge_points > 0 and total_points > (2 * edge_points):
                    # Split into left edge, middle, right edge
                    left_edge = water_y[:edge_points]
                    right_edge = water_y[-edge_points:]
                    middle = water_y[edge_points:-edge_points]
                    
                    # Use 25th percentile as baseline estimate (ignores peaks)
                    left_baseline = float(np.percentile(np.abs(left_edge), 25))
                    right_baseline = float(np.percentile(np.abs(right_edge), 25))
                    edge_baseline = (left_baseline + right_baseline) / 2
                    
                    middle_baseline = float(np.percentile(np.abs(middle), 25))
                    
                    # Calculate elevation ratio
                    if edge_baseline > 0:
                        elevation_ratio = middle_baseline / edge_baseline
                    else:
                        elevation_ratio = float('inf') if middle_baseline > 0 else 1.0
                    
                    # Check if middle is elevated (broad hump)
                    if elevation_ratio > BASELINE_ELEVATION_THRESHOLD:
                        water_check = 'CHECK'
                    else:
                        water_check = 'PASS'

            # Find matching row by spectrum name
            dfRows = qcDataTable.data.loc[qcDataTable.data['Spectrum'] == spectrumName]

            if len(dfRows) > 0:
                # Update existing row(s)
                for idx in dfRows.index:
                    qcDataTable.data.at[idx, 'Water_edge_baseline'] = edge_baseline
                    qcDataTable.data.at[idx, 'Water_middle_baseline'] = middle_baseline
                    qcDataTable.data.at[idx, 'Water_elevation_ratio'] = elevation_ratio
                    qcDataTable.data.at[idx, 'Water_check'] = water_check
            else:
                # Create new row if spectrum not found
                new_row = {
                    'Spectrum': spectrumName,
                    'Water_edge_baseline': edge_baseline,
                    'Water_middle_baseline': middle_baseline,
                    'Water_elevation_ratio': elevation_ratio,
                    'Water_check': water_check
                }
                qcDataTable.data = pd.concat([qcDataTable.data, pd.DataFrame([new_row])], ignore_index=True)

        return spectra


WaterPipe.register()
