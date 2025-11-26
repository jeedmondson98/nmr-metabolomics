#### GUI IMPORTS
from ccpn.ui.gui.widgets.PipelineWidgets import GuiPipe, _getWidgetByAtt
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.GLLinearRegionsPlot import GLTargetButtonSpinBoxes

#### NON GUI IMPORTS
from ccpn.framework.lib.pipeline.PipeBase import SpectraPipe, PIPE_USER
from ccpn.util.Logging import getLogger
import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_widths

########################################################################################################################
###   Attributes:
########################################################################################################################

PipeName = 'TSP Linewidth QC'

# Attribute names for GUI widgets
ReferenceRegion = 'Reference_Region'
DefaultReferenceRegion = (-0.2, 0.2)  # Default TSP region

# Spectrometer frequency (MHz) - adjust for your instrument
SPECTROMETER_FREQ_MHZ = 600  # Change this to match your NMR spectrometer frequency

########################################################################################################################
##########################################      ALGORITHM       ########################################################
########################################################################################################################

# Detect reference material peak and measure linewidth at half height (FWHM)
# Reference region: User-selectable via popup (default -0.2 to 0.2 ppm for TSP)
# Linewidth is reported in Hz

# ADJUST THESE TO CONTROL PEAK DETECTION SENSITIVITY
HEIGHT_THRESHOLD_PCT = 0.8        # Peaks must be at least 80% of max intensity
PROMINENCE_THRESHOLD_PCT = 0.3    # Peaks must stand out by at least 30%
ASYMMETRY_TOLERANCE = 0.15        # 15% tolerance

########################################################################################################################
##########################################     GUI PIPE    #############################################################
########################################################################################################################


class TSPLinewidthGuiPipe(GuiPipe):
    preferredPipe = True
    pipeName = PipeName

    def __init__(self, name=pipeName, parent=None, project=None, **kwds):
        super(TSPLinewidthGuiPipe, self).__init__(parent=parent, name=name, project=project, **kwds)
        self._parent = parent

        row = 0
        # Reference region selector
        self.regionLabel = Label(self.pipeFrame, text=ReferenceRegion, grid=(row, 0))
        setattr(self, ReferenceRegion, GLTargetButtonSpinBoxes(self.pipeFrame, application=self.application,
                                                               values=DefaultReferenceRegion, orientation='v',
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


class TSPLinewidthPipe(SpectraPipe):
    guiPipe = TSPLinewidthGuiPipe
    pipeName = PipeName
    pipeCategory = PIPE_USER

    _kwargs = {
        ReferenceRegion: DefaultReferenceRegion
    }

    def runPipe(self, spectra, **kwargs):
        """
        Measure reference material peak linewidth at half height and check for asymmetry.
        User can select the reference region via popup window.
        Linewidth is reported in Hz.
        TSP_check returns PASS if peak is symmetric, CHECK otherwise.
        """
        # Get reference region from GUI
        referenceRegion = self._kwargs[ReferenceRegion]
        
        # Pipe variables
        pipeColumns = ['Ref_peaks_detected', 'TSP_check', 'Ref_asymmetry_ratio', 'Ref_linewidth_Hz']

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

            # Get spectrometer frequency from spectrum if available
            spec_freq = SPECTROMETER_FREQ_MHZ
            if hasattr(spectrum, 'spectrometer') and spectrum.spectrometer:
                if hasattr(spectrum.spectrometer, 'frequency'):
                    spec_freq = spectrum.spectrometer.frequency

            # Normalize intensities
            y_norm = y / np.max(y)

            # Extract reference region (user-selected)
            region_min = min(referenceRegion[0], referenceRegion[1])
            region_max = max(referenceRegion[0], referenceRegion[1])
            
            ref_mask = (x >= region_min) & (x <= region_max)
            ref_x = x[ref_mask]
            ref_y = y_norm[ref_mask]

            # Find peaks in reference region
            peaks_detected = 0
            tsp_check = 'CHECK'
            asymmetry_ratio = float('nan')
            linewidth_Hz = float('nan')

            if len(ref_y) > 0:
                max_int = float(np.max(ref_y))
                height_thresh = max_int * HEIGHT_THRESHOLD_PCT
                prominence_thresh = max_int * PROMINENCE_THRESHOLD_PCT

                peaks, properties = find_peaks(
                    ref_y,
                    height=height_thresh,
                    prominence=prominence_thresh
                )

                peaks_detected = int(len(peaks))

                # Check symmetry only if we found exactly 1 peak
                if peaks_detected == 1:
                    peak_index = peaks[0]
                    
                    # Split the peak into left and right halves
                    left_half = ref_y[:peak_index + 1]
                    right_half = ref_y[peak_index:]
                    
                    # Find max height on each side
                    left_max = float(np.max(left_half)) if len(left_half) > 0 else 0
                    right_max = float(np.max(right_half)) if len(right_half) > 0 else 0
                    
                    # Calculate asymmetry ratio
                    if left_max > 0 and right_max > 0:
                        ratio = min(left_max, right_max) / max(left_max, right_max)
                        asymmetry_ratio = ratio
                        
                        lower_bound = 1.0 - ASYMMETRY_TOLERANCE
                        if ratio >= lower_bound:
                            tsp_check = 'PASS'
                        else:
                            tsp_check = 'CHECK'
                    else:
                        tsp_check = 'CHECK'

                    # Calculate linewidth at half height in ppm first
                    widths_res = peak_widths(ref_y, peaks, rel_height=0.5)
                    spacing_ppm = float(abs(ref_x[1] - ref_x[0])) if len(ref_x) > 1 else 1.0
                    widths_ppm = widths_res[0] * spacing_ppm
                    idx_max = int(np.argmax(properties['peak_heights']))
                    linewidth_ppm = float(widths_ppm[idx_max])
                    
                    # Convert linewidth from ppm to Hz
                    linewidth_Hz = linewidth_ppm * spec_freq

            # Find matching row by spectrum name
            dfRows = qcDataTable.data.loc[qcDataTable.data['Spectrum'] == spectrumName]

            if len(dfRows) > 0:
                # Update existing row(s)
                for idx in dfRows.index:
                    qcDataTable.data.at[idx, 'Ref_peaks_detected'] = peaks_detected
                    qcDataTable.data.at[idx, 'TSP_check'] = tsp_check
                    qcDataTable.data.at[idx, 'Ref_asymmetry_ratio'] = asymmetry_ratio
                    qcDataTable.data.at[idx, 'Ref_linewidth_Hz'] = linewidth_Hz
            else:
                # Create new row if spectrum not found
                new_row = {
                    'Spectrum': spectrumName,
                    'Ref_peaks_detected': peaks_detected,
                    'TSP_check': tsp_check,
                    'Ref_asymmetry_ratio': asymmetry_ratio,
                    'Ref_linewidth_Hz': linewidth_Hz
                }
                qcDataTable.data = pd.concat([qcDataTable.data, pd.DataFrame([new_row])], ignore_index=True)

        return spectra


TSPLinewidthPipe.register()
